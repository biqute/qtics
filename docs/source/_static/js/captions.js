// Make each sidebar section title a link to the first page of its section
document.addEventListener("DOMContentLoaded", () => {
  for (const caption of document.querySelectorAll(".sidebar-tree p.caption")) {
    const first = caption.nextElementSibling?.querySelector("a.reference");
    const text = caption.querySelector(".caption-text");
    if (!first || !text)
      continue;
    const link = document.createElement("a");
    link.href = first.getAttribute("href");
    link.className = "caption-link";
    text.replaceWith(link);
    link.append(text);
  }
});
