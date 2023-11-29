"""S21 versus temperature."""

import time
from datetime import datetime

import h5py
import numpy as np

from qinst import VNAN9916A, Triton, log

FILE_NAME = "data"

DELAY_BETWEEN_ACQ: float = 1  # minutes
TOTAL_ACQUISITION_TIME: float = 60 * 10  # minutes

START = 1e9  # Hz
STOP = 4e9  # Hz
SIZE = 0.5e9  # Hz


triton = Triton("triton")
triton.connect()
vna = VNAN9916A("vna", "192.168.40.10")
vna.set(sweep_points=1600, power=-30, average=1)

path = f"{FILE_NAME}-{time.strftime('%m/%d_%H:%M:%S')}.hdf5"


def save_data(
    date: str, temperature: float, frequencies: np.ndarray, values: np.ndarray
):
    """Save data appending to hdf5 file."""
    with h5py.File(path, "a") as file:
        # Create a unique group for each acquisition
        group_name = f"{date}_T{temperature}"
        group = file.create_group(group_name)

        # Save metadata
        group.attrs["date"] = date
        group.attrs["temperature"] = temperature

        # Save data
        group.create_dataset("frequencies", data=frequencies)
        group.create_dataset("values", data=values)


def main():
    """Acquisition function."""
    for _ in range(int(TOTAL_ACQUISITION_TIME / DELAY_BETWEEN_ACQ)):
        try:
            date = str(datetime.now())
            log.info(f"Acquisition started.")
            temperature = triton.get_mixing_chamber_temp()
            log.info(f"Temperature: {round(temperature, 2)} mK.")
            frequencies, values = vna.survey(
                f_win_start=START, f_win_end=STOP, f_win_size=SIZE
            )

            save_data(date, temperature, frequencies, values)
            log.info(f"Single acquisition completed.")
        except KeyboardInterrupt:
            log.warning("Interrupt signal received, exiting")
            break
        except Exception as e:
            log.error(f"\n\nException occured: {e}")
        finally:
            time.sleep(DELAY_BETWEEN_ACQ * 60)
        log.info("Acquisition completed. Closing.")


if __name__ == "__main__":
    main()
