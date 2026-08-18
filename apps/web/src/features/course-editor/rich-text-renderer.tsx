import { Fragment, type ReactNode } from "react";

import type { components } from "@ai-lms/api-client";

type RichTextDocument = components["schemas"]["RichTextDocument"];
type TextNode = components["schemas"]["TextNode"];
type ParagraphNode = components["schemas"]["ParagraphNode"];

function renderText(node: TextNode, key: string): ReactNode {
  let content: ReactNode = node.text;
  for (const mark of node.marks) {
    if (mark === "strong") {
      content = <strong>{content}</strong>;
    } else if (mark === "emphasis") {
      content = <em>{content}</em>;
    } else if (mark === "code") {
      content = <code>{content}</code>;
    }
  }
  return <Fragment key={key}>{content}</Fragment>;
}

function renderParagraph(node: ParagraphNode, key: string): ReactNode {
  return <p key={key}>{node.content.map((text, index) => renderText(text, `${key}-${index}`))}</p>;
}

export function RichTextRenderer({ document }: { document: RichTextDocument }) {
  if (document.type !== "document" || !Array.isArray(document.content)) {
    return <p>Unsupported course content.</p>;
  }

  return document.content.map((node, index) => {
    const key = `block-${index}`;
    if (node.type === "paragraph") {
      return renderParagraph(node, key);
    }
    if (node.type === "heading") {
      const content = node.content.map((text, textIndex) =>
        renderText(text, `${key}-${textIndex}`),
      );
      if (node.level === 2) {
        return <h2 key={key}>{content}</h2>;
      }
      if (node.level === 3) {
        return <h3 key={key}>{content}</h3>;
      }
      return <h4 key={key}>{content}</h4>;
    }
    if (node.type === "bullet_list" || node.type === "ordered_list") {
      const items = node.items.map((item, itemIndex) => (
        <li key={`${key}-${itemIndex}`}>
          {item.content.map((paragraph, paragraphIndex) =>
            renderParagraph(paragraph, `${key}-${itemIndex}-${paragraphIndex}`),
          )}
        </li>
      ));
      return node.type === "bullet_list" ? <ul key={key}>{items}</ul> : <ol key={key}>{items}</ol>;
    }
    return null;
  });
}
