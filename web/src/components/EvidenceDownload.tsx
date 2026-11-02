import type { ComparisonData } from "../types";

/** Export only the result-backed comparison currently being inspected. */
export function EvidenceDownload({ data }: { data: ComparisonData }) {
  const download = () => {
    const blob = new Blob([`${JSON.stringify(data, null, 2)}\n`], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "field-quality-comparison.json";
    anchor.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  return <button type="button" className="btn btn-secondary" onClick={download}>Download comparison</button>;
}
