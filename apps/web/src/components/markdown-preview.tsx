import { Fragment } from "react";

export function MarkdownPreview({ text }: { text: string }) {
  const blocks = text.split(/(```[^\n]*\n[\s\S]*?```)/g);
  return (
    <div className="markdown-preview">
      {blocks.map((block, index) => {
        if (block.startsWith("```"))
          return (
            <pre key={index}>
              <code>
                {block.replace(/^```[^\n]*\n/, "").replace(/```$/, "")}
              </code>
            </pre>
          );
        return (
          <Fragment key={index}>
            {block
              .split(/\n\s*\n/)
              .filter(Boolean)
              .map((paragraph, i) => {
                const rows = paragraph.split("\n");
                if (rows.every((row) => /^[-*] /.test(row)))
                  return (
                    <ul key={i}>
                      {rows.map((row, j) => (
                        <li key={j}>{row.slice(2)}</li>
                      ))}
                    </ul>
                  );
                return <p key={i}>{paragraph.replace(/^#{1,6} /gm, "")}</p>;
              })}
          </Fragment>
        );
      })}
    </div>
  );
}
