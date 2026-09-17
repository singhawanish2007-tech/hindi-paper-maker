import React, { useMemo } from "react";

interface FormattedTextProps {
  text?: string;
  className?: string;
}

const ALLOWED_TAGS = new Set(["U", "B", "STRONG", "I", "EM", "BR", "SPAN", "P", "UL", "OL", "LI"]);

export const FormattedText: React.FC<FormattedTextProps> = ({ text = "", className = "" }) => {
  const sanitizedHtml = useMemo(() => {
    if (!text) return "";
    if (!text.includes("<")) {
      return text.replace(/\n/g, "<br/>");
    }
    try {
      const parser = new DOMParser();
      const doc = parser.parseFromString(`<div>${text}</div>`, "text/html");

      const cleanNode = (node: Node): Node | null => {
        if (node.nodeType === Node.TEXT_NODE) {
          return node.cloneNode(true);
        }
        if (node.nodeType === Node.ELEMENT_NODE) {
          const el = node as HTMLElement;
          const tagName = el.tagName.toUpperCase();
          if (!ALLOWED_TAGS.has(tagName)) {
            const fragment = document.createDocumentFragment();
            Array.from(el.childNodes).forEach((child) => {
              const cleaned = cleanNode(child);
              if (cleaned) fragment.appendChild(cleaned);
            });
            return fragment;
          }
          const cleanEl = document.createElement(tagName.toLowerCase());
          Array.from(el.childNodes).forEach((child) => {
            const cleaned = cleanNode(child);
            if (cleaned) cleanEl.appendChild(cleaned);
          });
          return cleanEl;
        }
        return null;
      };

      const root = doc.body.firstElementChild;
      if (!root) return text;

      const cleanContainer = document.createElement("div");
      Array.from(root.childNodes).forEach((child) => {
        const cleaned = cleanNode(child);
        if (cleaned) cleanContainer.appendChild(cleaned);
      });

      return cleanContainer.innerHTML.replace(/\n/g, "<br/>");
    } catch {
      return text;
    }
  }, [text]);

  return (
    <span
      className={`formatted-text ${className}`}
      dangerouslySetInnerHTML={{ __html: sanitizedHtml }}
    />
  );
};
