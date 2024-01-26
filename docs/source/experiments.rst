.. _experiments:

Experiments
===========

Qtics helps coordinating multiple instruments and provides simple data handling functions through the ``Experiment`` classes. A basic example can be found in the `examples <https://github.com/biqute/qtics/tree/main/examples>`_ folder.

New experiments can be created using the :class:`qtics.experiment.Experiment` and :class:`qtics.experiment.MonitorExperiment` classes, which both inherit from :class:`qtics.experiment.BaseExperiment`. Some of the provided functionalities include:

- Call methods common to all instruments
- Simplified data saving and loading functions with hdf5 files
- Automatic save of the instruments defaults and experiment's attributes in the data file
- Reset the instruments when exceptions occurs.
- Monitor in parallel the parameters of other instruments and interrupt the experiment if chosen conditions are not satisfied.

Writing a new experiment
""""""""""""""""""""""""
All new experiments classes must satisfy two requirements:

- All the instruments used in the experiment must be specified in the class definition, either as instances or with type annotations. Instruments can be added only if their name corresponds to the experiment's attribute.
- A ``main()`` method must be implemented

Here's an example of a simple experiment that acquires and saves a `VNA <https://biqute.github.io/qtics/instruments/N9916A.html>`_ snapshot.

.. code-block:: python

  from qtics import VNAN9916A, Experiment

  class VNASnapshot(Experiment):
      """Simple snapshot with vna."""

      vna = VNAN9916A("vna", "address")

      def main(self):
          """Acquire VNA snapshot."""
          self.vna.connect()
          f, z = self.vna.snapshot()
          self.append_data_group("snapshot", datasets={"frequencies": f, "values": z})
          self.save_config()

The experiment can be launched by calling the ``run()`` method, which will execute ``main()`` while controlling for exceptions and errors.

.. code-block:: python

   exp = VNASnapshot("vna_snapshot")
   exp.run()

This will create a ``vna_snapshot_{current_date}.hdf5`` file with the acquired data.

MonitorExperiment
"""""""""""""""""

The experiment classes allow to monitor in parallel the parameters of other instruments and reset the experiment if they do not respect some chosen condition. This can be done by writing a class derived from :class:``qtics.experiment.MonitorExperiment`` and adding it to the main experiment.
Their main features consist of:

- The ``main`` method a ``MonitorExperiment`` is run every ``MonitorExperiment.sleep`` seconds.
- The reset and stop condition is activated by raising an ``Exception``

Here's an example of a ``MonitorExperiment`` that checks if the temperature of the cryostat is in the allowed range.

.. code-block:: python

  class TemperatureMonitor(MonitorExperiment):

      cryo = Triton("name", "address")
      min_temp = 20
      max_temp = 60
      sleep = 5

      def main(self):
          """Check if temperature is in range."""
          temperature = self.cryo.get_mixing_chamber_temp()
          if temperature < self.min_temp or temperature > self.max_temp:
              raise Exception("Temperature %s mK out of allowed range.", temperature)


In the main experiment, the reset condition can be checked by calling the ''Experiment.monitor_failed()`` method, as in this example.

.. code-block:: python

  class MultiVNASnapshot(Experiment):
      """Multiple vna snapshots with temperature checks."""

      vna = VNAN9916A("vna", "address")
      monitors = [TemperatureMonitor("tempcheck")]
      n_snapshots = 20

      def main(self):
          """Acquire VNA snapshot."""
          self.vna.connect()
          for i in range(self.n_snapshots):
              f, z = self.vna.snapshot()
              self.append_data_group(f"snapshot_{i}", datasets={"frequencies": f, "values": z})
              if self.monitor_failed()
                  return
          self.save_config()
