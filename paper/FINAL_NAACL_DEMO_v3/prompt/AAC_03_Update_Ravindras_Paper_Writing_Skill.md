# Claude Code prompt 3 — Update ravindras-paper-writing-skill

Update the existing "ravindras-paper-writing-skill" that the user invokes as "/ravindras-paper-writing-skill". Resolve the active editable source using the current project's ".claude/skills/" and the user's "~/.claude/skills/" or configured equivalent. Read its "SKILL.md", frontmatter, and any bibliography or LaTeX references it loads. If multiple copies exist, verify which one the slash command loads and target the user's editable source. If a managed or synced copy is active, locate its editable source or report the exact location that the user must update. Keep the skill's identity and scope. Add a concise policy to the existing relevant section or reference. See [Claude Code skill documentation](https://code.claude.com/docs/en/skills).

## Add these writing rules

1. **Evidence and prose.** Use natural US English, specific scientific claims, and a clear distinction between the method, measurements, and interpretation. Read the project evidence handoff before inserting results. Preserve the evaluated scope, denominators, and uncertainty. Place author actions and missing dependencies in a revision note outside the manuscript. Use exact model and dataset names, with restrained first-mention emphasis at the template's normal point size and typewriter styling for literal identifiers where appropriate.
2. **Native scripts.** Use properly shaped Unicode text and a locale-appropriate OpenType font with the publisher's XeLaTeX or LuaLaTeX workflow where supported. Keep native-script examples upright by default and use clear language labels and italic English glosses. Preserve glyphs, combining marks, punctuation, and text extraction. Example strings to validate are Hindi "मुझे पानी चाहिए।", Gujarati "મને પાણી જોઈએ છે.", and Marathi "मला पाणी हवे आहे." Distinguish authored examples from quoted system outputs.
3. **Web access dates.** When a web footnote or reference calls for an access date, display "Last Accessed Date: September 3rd, 2026", substituting the actual verified date for that resource. Use US month–day–year order and a correct ordinal suffix, including the 11th, 12th, and 13th exceptions. The September date is a formatting example. Keep publication year and access date in separate fields. Use "urldate" in ISO format when the bibliography backend supports it, or a style-compatible note or normal body-text footnote when it does not. Avoid duplicating the access date across a footnote and its reference.
4. **Bibliographic metadata.** Use "@article" for a journal paper, "@inproceedings" for a conference proceedings paper, and an appropriate supported type for a preprint, model card, or website. Verify metadata from the publisher or repository. Use the proceedings' full title in "booktitle" for a conference paper, and the journal title in "journal" for an article. Store a numeric publication "year" and a separate "address" or backend-specific location field when the venue location is supported and verified. Put numeric volume in "volume", issue in "number" if applicable, and a verified page range such as "5767--5777" in "pages". Preserve article numbers as article numbers. Protect scientific acronyms and proper names from automatic case changes.
5. **Volume and page labels.** In a user-controlled prose reference or bibliography, render "vol. 30", "pp. 5767–5777" for a range, and "p. 5767" for one page, following the target style. In a venue submission, use the mandated formatter's output. Keep prefixes, location, and pagination in separate metadata fields so the bibliography does not emit duplicate labels. Follow the required ACL class and bibliography style for ACL-family venues.

## Add or update the formatting examples

Use a normal text footnote for a verified web access date. This example uses a sample resource and a sample date.

~~~latex
\footnote{\url{https://example.org/resource}
  (Last Accessed Date: September 3\textsuperscript{rd}, 2026).}
~~~

Use this conference entry to validate field structure. The official proceedings verify the title, authors, volume and page range, and the organizer verifies Long Beach as the location. [NeurIPS proceedings](https://proceedings.neurips.cc/paper_files/paper/2017/hash/892c3b1c6dccd52936e27cbd0ff683d6-Abstract.html) · [Publisher metadata](https://proceedings.neurips.cc/paper_files/paper/2017/file/892c3b1c6dccd52936e27cbd0ff683d6-Metadata.json) · [Conference location](https://neurips.cc/Conferences/2017)

~~~bibtex
@inproceedings{gulrajani2017improved,
  author    = {Gulrajani, Ishaan and Ahmed, Faruk and Arjovsky, Martin
               and Dumoulin, Vincent and Courville, Aaron C.},
  title     = {Improved Training of {Wasserstein} {GANs}},
  booktitle = {Advances in Neural Information Processing Systems},
  volume    = {30},
  pages     = {5767--5777},
  year      = {2017},
  address   = {Long Beach, California, USA},
  url       = {https://proceedings.neurips.cc/paper_files/paper/2017/hash/892c3b1c6dccd52936e27cbd0ff683d6-Abstract.html}
}
~~~

In a prose or custom-style reference, the volume and pages can appear as "Advances in Neural Information Processing Systems, vol. 30, pp. 5767–5777".

## Validate the update

Validate the skill's frontmatter and linked reference paths. Exercise the updated rules with the conference example, a journal paper with volume and issue, and a model-card footnote with a verified access date. Check that each field appears once and that ACL output follows its official style. If TeX is available, compile a minimal footnote and three-script example and inspect the PDF for glyphs and font embedding. Verify that the slash command resolves to the revised guidance. Report the exact modified path, a concise summary of the diff, and the actual verification results.
