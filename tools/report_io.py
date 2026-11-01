import html
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor


class Paper:
    def __init__(self, title, subtitle):
        self.title, self.subtitle, self.blocks = title, subtitle, []

    def p(self, text):
        self.blocks.append(("p", text))

    def h(self, text, level=1):
        self.blocks.append(("h", (text, level)))

    def table(self, headers, rows):
        assert all(len(row) == len(headers) for row in rows), "表格列数不一致"
        self.blocks.append(("table", (headers, rows)))

    def figure(self, path, caption):
        self.blocks.append(("figure", (str(path), caption)))


def font(run, size=10.5, bold=False):
    run.font.name = "宋体"
    run.font.size = Pt(size)
    run.bold = bold
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), "宋体")


def table_widths(headers):
    # Long test identifiers need more room than the short result/duration cells.
    return [70, 15, 15] if headers == ["测试项", "实际结果", "耗时ms"] else None


def render_docx(paper, path):
    d = Document()
    s = d.sections[0]
    s.page_width, s.page_height = Cm(21), Cm(29.7)
    s.top_margin, s.bottom_margin = Cm(1.8), Cm(1.8)
    s.left_margin = s.right_margin = Cm(1.8)
    normal = d.styles["Normal"]
    normal.font.name = "宋体"
    normal.font.size = Pt(10.5)
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.18
    for style, size in [("Title", 19), ("Heading 1", 14), ("Heading 2", 11.5)]:
        a = d.styles[style]
        a.font.name = "微软雅黑"
        a.font.size = Pt(size)
        a._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")
        a.font.color.rgb = RGBColor.from_string("17324D")
    d.add_heading(paper.title, 0)
    d.add_paragraph(paper.subtitle)
    for kind, value in paper.blocks:
        if kind == "h":
            d.add_heading(value[0], value[1])
        elif kind == "p":
            d.add_paragraph(value)
        elif kind == "figure":
            d.add_picture(value[0], width=Cm(17.2))
            d.add_paragraph(value[1])
        else:
            headers, rows = value
            t = d.add_table(rows=1, cols=len(headers))
            t.style = "Table Grid"
            widths = table_widths(headers)
            if widths:
                t.autofit = False
                for column, width in zip(t.columns, widths):
                    column.width = Cm(17.4 * width / 100)
            for c, v in zip(t.rows[0].cells, headers):
                c.text = str(v)
                for run in c.paragraphs[0].runs:
                    font(run, size=9, bold=True)
            repeat = OxmlElement("w:tblHeader")
            t.rows[0]._tr.get_or_add_trPr().append(repeat)
            for row in rows:
                cells = t.add_row().cells
                if widths:
                    for cell, width in zip(cells, widths):
                        cell.width = Cm(17.4 * width / 100)
                for c, v in zip(cells, row):
                    c.text = str(v)
                    for p in c.paragraphs:
                        p.paragraph_format.space_after = Pt(3)
                        p.paragraph_format.line_spacing = 1.08
                        for r in p.runs:
                            font(r, size=9)
            d.add_paragraph()
    f = s.footer.paragraphs[0]
    f.alignment = 2
    font(f.add_run("软件工程团队项目 | 知页1.0 | "), size=8)
    page = OxmlElement("w:fldSimple")
    page.set(qn("w:instr"), "PAGE")
    f._p.append(page)
    d.core_properties.title = paper.title
    d.core_properties.author = "知页小组"
    d.core_properties.subject = "软件工程团队课程项目"
    d.save(path)


CSS = """@page{size:A4;margin:17mm 17mm 16mm}*{box-sizing:border-box}body{font-family:"Microsoft YaHei","SimSun",sans-serif;font-size:10pt;line-height:1.5;color:#172333}h1{font-size:19pt;color:#17324d;margin:0 0 10pt}h2{font-size:14pt;margin:16pt 0 6pt;break-after:avoid;color:#17324d}h3{font-size:11.5pt;margin:11pt 0 5pt;break-after:avoid}p{margin:0 0 7pt;orphans:2;widows:2}.subtitle{font-size:9pt;color:#596777;margin-bottom:13pt}table{border-collapse:collapse;width:100%;table-layout:fixed;font-size:9pt;margin:7pt 0 10pt}th,td{border:1px solid #ccd5df;padding:5.5pt;vertical-align:top;overflow-wrap:anywhere}th{background:#eef3f8;text-align:left}thead{display:table-header-group}tr{break-inside:avoid}th:first-child{width:17%}figure{margin:10pt 0;break-inside:avoid}figure img{width:100%}figcaption{font-size:9pt;color:#596777;margin-top:5pt}"""


def render_html(paper, path):
    buf = [
        '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>'
        + html.escape(paper.title)
        + "</title><style>"
        + CSS
        + "</style><body><h1>"
        + html.escape(paper.title)
        + '</h1><p class="subtitle">'
        + html.escape(paper.subtitle)
        + "</p>"
    ]
    for kind, v in paper.blocks:
        if kind == "p":
            buf.append("<p>" + html.escape(v) + "</p>")
        elif kind == "h":
            tag = "h" + str(v[1] + 1)
            buf.append("<" + tag + ">" + html.escape(v[0]) + "</" + tag + ">")
        elif kind == "figure":
            buf.append(
                '<figure><img src="'
                + html.escape(Path(v[0]).as_uri())
                + '"><figcaption>'
                + html.escape(v[1])
                + "</figcaption></figure>"
            )
        else:
            headers, rows = v
            widths = table_widths(headers)
            buf.append(
                "<table><thead><tr>"
                + "".join(
                    (f'<th style="width:{widths[i]}%">' if widths else "<th>")
                    + html.escape(str(c))
                    + "</th>"
                    for i, c in enumerate(headers)
                )
                + "</tr></thead><tbody>"
            )
            buf.extend(
                "<tr>"
                + "".join("<td>" + html.escape(str(c)) + "</td>" for c in row)
                + "</tr>"
                for row in rows
            )
            buf.append("</tbody></table>")
    path.write_text("".join(buf) + "</body></html>", encoding="utf-8")
