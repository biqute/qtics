// Fill the sidebar version switcher from versions.json at the site root.
// versions.json: [{"name": "latest", "version": "0.1.0", "url":
// "https://.../qtics/"}, ...]
document.addEventListener("DOMContentLoaded", async () => {
  const select = document.getElementById("qt-version-select");
  if (!select)
    return;
  select.disabled = true;
  select.title = "Other versions are listed only on the published site";
  let versions;
  try {
    const response = await fetch(select.dataset.versions, {cache : "no-cache"});
    if (!response.ok)
      return;
    versions = await response.json();
  } catch (error) {
    return; // local build or offline: keep the current release only
  }
  const here = window.location.href;
  // The current version is the one with the longest url prefixing this page
  const current = versions.filter((v) => here.startsWith(v.url))
                      .sort((a, b) => b.url.length - a.url.length)[0];
  if (!current)
    return; // page not served from the published site
  select.replaceChildren(...versions.map((v) => {
    const label =
        v.version && v.version !== v.name ? `${v.name} (${v.version})` : v.name;
    return new Option(label, v.url, v === current, v === current);
  }));
  select.disabled = false;
  select.title = "Switch documentation version";
  select.addEventListener("change", async () => {
    const page = here.slice(current.url.length).split("#")[0];
    const target = select.value + page;
    try {
      const response = await fetch(target, {method : "HEAD"});
      window.location.href = response.ok ? target : select.value;
    } catch (error) {
      window.location.href = select.value;
    }
  });
});
