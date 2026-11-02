import test from "node:test";
import assert from "node:assert/strict";
import { findInNoteText } from "../src/noteFind.js";
import { mergeFindRanges, snapshotPreview } from "../src/noteFindDOM.js";

test("empty text, empty query and whitespace-only query have no matches", () => {
  for (const [text, query] of [["", "AI"], ["AI", ""], ["AI", " \t\n"]]) {
    assert.deepEqual(findInNoteText(text, query), []);
  }
});
test("Chinese substring occurrences preserve original offsets", () => {
  assert.deepEqual(findInNoteText("动态规划与动态规划", "动态规划"), [[0, 4], [5, 9]]);
});
test("ASCII case is ignored for every occurrence", () => {
  assert.deepEqual(findInNoteText("AI ai Ai", "aI"), [[0, 2], [3, 5], [6, 8]]);
});
test("emoji offsets count Unicode code points, not UTF-16 units", () => {
  assert.deepEqual(findInNoteText("😀AI😀ai", "ai"), [[1, 3], [4, 6]]);
  assert.deepEqual(findInNoteText("😀😀", "😀"), [[0, 1], [1, 2]]);
});
test("overlapping hits stay separate for future hit counts and navigation", () => {
  assert.deepEqual(findInNoteText("ababa", "aba"), [[0, 3], [2, 5]]);
  assert.deepEqual(findInNoteText("aaaa", "aa"), [[0, 2], [1, 3], [2, 4]]);
});
test("adjacent occurrences are not merged", () => {
  assert.deepEqual(findInNoteText("AIai", "AI"), [[0, 2], [2, 4]]);
});
test("the whole query is a literal phrase, not AND tokens", () => {
  assert.deepEqual(findInNoteText("AI学习动态规划；AI 动态规划", "AI 动态规划"), [[9, 16]]);
});
test("meaningful spaces and line breaks are not collapsed", () => {
  assert.deepEqual(findInNoteText(" AI  AI ", " AI "), [[0, 4], [4, 8]]);
  assert.deepEqual(findInNoteText("A\nB A B", "a\nb"), [[0, 3]]);
});
test("regular-expression symbols and HTML-looking text remain literal", () => {
  assert.deepEqual(findInNoteText("[a]+ [a]+", "[a]+"), [[0, 4], [5, 9]]);
  assert.deepEqual(findInNoteText("<script>AI</script>", "AI"), [[8, 10]]);
});
test("Unicode case and composition are not silently changed", () => {
  assert.deepEqual(findInNoteText("Å å Å", "å"), [[2, 3]]);
  assert.deepEqual(findInNoteText("e\u0301 é", "é"), [[3, 4]]);
});
test("missing and longer queries have no matches", () => {
  assert.deepEqual(findInNoteText("动态规划", "不存在"), []);
  assert.deepEqual(findInNoteText("AI", "AI 模型"), []);
});
test("wrong input types are rejected before searching", () => {
  for (const value of [null, undefined, 42, {}, []]) {
    assert.throws(() => findInNoteText(value, "AI"), TypeError);
    assert.throws(() => findInNoteText("AI", value), TypeError);
  }
});
test("calls return independent arrays without modifying inputs", () => {
  const first = findInNoteText("AI AI", "AI");
  first[0][0] = 99;
  assert.deepEqual(findInNoteText("AI AI", "AI"), [[0, 2], [3, 5]]);
});
test("long repeated-prefix text returns the exact distant match", { timeout: 5000 }, () => {
  assert.deepEqual(findInNoteText("a".repeat(300000) + "b", "a".repeat(5000) + "b"),
    [[295000, 300001]]);
});
test("500 deterministic generated cases agree with a naive code-point oracle", () => {
  let state = 20261102;
  const next = () => (state = (Math.imul(state, 1664525) + 1013904223) >>> 0);
  const alphabet = ["A", "a", "I", "i", "中", "😀", " ", "\n", "."];
  for (let sample = 0; sample < 500; sample++) {
    const text = Array.from({ length: next() % 80 }, () => alphabet[next() % alphabet.length]).join("");
    const query = Array.from({ length: next() % 7 }, () => alphabet[next() % alphabet.length]).join("");
    const chars = Array.from(text.toLowerCase());
    const wanted = Array.from(query.toLowerCase());
    const expected = [];
    if (query.trim()) {
      for (let i = 0; i <= chars.length - wanted.length; i++) {
        if (chars.slice(i, i + wanted.length).join("") === wanted.join("")) {
          expected.push([i, i + wanted.length]);
        }
      }
    }
    assert.deepEqual(findInNoteText(text, query), expected, `sample ${sample}`);
  }
});

test("highlight unions do not change overlapping hit counts or input ranges", () => {
  const matches = findInNoteText("aaaa", "aa");
  const original = structuredClone(matches);
  assert.equal(matches.length, 3);
  assert.deepEqual(mergeFindRanges(matches), [[0, 4]]);
  assert.deepEqual(matches, original);
  assert.deepEqual(mergeFindRanges([[0, 2], [2, 4], [7, 9]]), [[0, 4], [7, 9]]);
  assert.deepEqual(mergeFindRanges([]), []);
});
test("missing preview during mount returns an empty safe snapshot", () => {
  assert.deepEqual(snapshotPreview(null), { text: "", locations: [] });
});
