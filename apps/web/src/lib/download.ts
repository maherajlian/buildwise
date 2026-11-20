export function downloadMarkdown(text: string, filename: string) {
  downloadText(text, filename, "text/markdown;charset=utf-8");
}
export function downloadCsv(text: string, filename: string) {
  downloadText(text, filename, "text/csv;charset=utf-8");
}
function downloadText(text: string, filename: string, type: string) {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}
