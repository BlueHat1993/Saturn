import { Fragment, type ReactNode } from 'react';

const BOLD_PATTERN = /\*\*(.+?)\*\*/g;
const HEADING_PATTERN = /^(#{1,6})\s+(.*)$/;

function sanitizeLine(line: string): string {
  const match = line.match(HEADING_PATTERN);
  return match ? match[2] : line;
}

function renderInline(text: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  let lastIndex = 0;
  let key = 0;

  for (const match of text.matchAll(BOLD_PATTERN)) {
    const index = match.index ?? 0;
    if (index > lastIndex) {
      nodes.push(<Fragment key={key++}>{text.slice(lastIndex, index)}</Fragment>);
    }
    nodes.push(<strong key={key++}>{match[1]}</strong>);
    lastIndex = index + match[0].length;
  }

  if (lastIndex < text.length) {
    nodes.push(<Fragment key={key++}>{text.slice(lastIndex)}</Fragment>);
  }

  return nodes.length > 0 ? nodes : [text];
}

export function MessageContent({ content }: { content: string }) {
  const lines = content.split('\n');

  return (
    <>
      {lines.map((line, index) => {
        const sanitized = sanitizeLine(line);
        return (
          <Fragment key={index}>
            {index > 0 && <br />}
            {renderInline(sanitized)}
          </Fragment>
        );
      })}
    </>
  );
}
