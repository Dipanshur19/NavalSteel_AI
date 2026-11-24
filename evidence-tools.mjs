const words = (text) =>
  text
    .toLowerCase()
    .normalize("NFKC")
    .match(/[\p{L}\p{N}]+/gu) || [];
export function searchPassages(docs, query, scope) {
  const terms = [...new Set(words(query))];
  if (!terms.length) return [];
  const entries = [];
  for (const doc of docs) {
    if (scope !== "all" && doc.id !== scope) continue;
    for (const page of doc.pages) {
      for (const [index, paragraph] of page.paragraphs.entries()) {
        const tokens = words(paragraph);
        if (tokens.length < 4) continue;
        entries.push({
          doc: doc.id,
          title: doc.title,
          page: page.page,
          index,
          paragraph,
          tokens: new Set(tokens),
        });
      }
    }
  }
  const weights = terms.map((t) =>
    Math.log(
      1 +
        (1 + entries.length) /
          (1 + entries.filter((e) => e.tokens.has(t)).length),
    ),
  );
  const results = [];
  for (const e of entries) {
    const hits = terms.filter((t) => e.tokens.has(t));
    if (!hits.length) continue;
    let score =
      (terms.reduce(
        (sum, t, i) => sum + (e.tokens.has(t) ? weights[i] : 0),
        0,
      ) *
        hits.length) /
      terms.length;
    if (e.paragraph.toLowerCase().includes(query.toLowerCase().trim()))
      score *= 1.6;
    results.push({
      doc: e.doc,
      title: e.title,
      page: e.page,
      index: e.index,
      paragraph: e.paragraph,
      score,
    });
  }
  return results
    .sort((a, b) => b.score - a.score || a.page - b.page)
    .slice(0, 10);
}
export function passageKey(hit) {
  return [hit.doc, hit.page, hit.index].join(":");
}
export function snippet(text, q) {
  if (text.length < 480) return text;
  const at = words(q)
    .map((t) => text.toLowerCase().indexOf(t))
    .filter((v) => v >= 0);
  const start = at.length ? Math.max(0, Math.min(...at) - 100) : 0;
  return (
    (start ? "… " : "") +
    text.slice(start, start + 460) +
    (start + 460 < text.length ? " …" : "")
  );
}
