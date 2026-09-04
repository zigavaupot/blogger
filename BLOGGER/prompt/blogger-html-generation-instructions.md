# Blogger HTML Generation Instructions

Use these instructions whenever converting a Markdown blog post into HTML for publishing on **zigavaupot.blogspot.com**.

The output must be ready to paste directly into the **HTML view of a Blogger post**.

---

## 1. General Objective

Convert the supplied Markdown document into clean, semantic Blogger-ready HTML while preserving:

- the complete meaning and structure of the source Markdown;
- headings, paragraphs, lists, tables, code blocks, links, images, and other meaningful content;
- the order of the source content;
- technical formatting such as inline code and preformatted code blocks.

Do not summarize, shorten, rewrite, or omit content unless explicitly requested.

Do not invent content that is not present in the source Markdown.

---

## 2. Do Not Embed CSS

Do **not** include:

```html
<style>...</style>
```

Do **not** copy the contents of `blogger-post.css` into the post.

Do **not** add an external stylesheet `<link>` inside the post.

The Blogger theme is responsible for loading the shared external stylesheet used by generated posts.

All generated article HTML must use the existing CSS class namespace, especially:

```html
<article class="zv-blog-post">
```

This allows one centrally maintained stylesheet to control the appearance of all generated posts.

---

## 3. Required Top-Level Structure

Every generated post must use this structure:

```html
<article class="zv-blog-post">

  <!-- Featured image / opening image -->

  <!-- Short description / introduction -->
  <div class="post-intro">
    ...
  </div>

  <!--more-->

  <!-- Main article content -->
  ...

</article>
```

There must be exactly one outer:

```html
<article class="zv-blog-post">
```

wrapper.

Do not add another `<article>` wrapper around it.

---

## 4. Post Preview Structure and Blogger Jump Break

The beginning of the post has a special purpose.

Everything before:

```html
<!--more-->
```

is the **post preview section**.

This section is used by Blogger listing pages such as:

- Home / Latest Posts
- Posts
- Series
- label pages
- archive pages
- search results

The preview section must contain:

1. the opening / featured image;
2. a concise but meaningful short description of the article.

Then insert:

```html
<!--more-->
```

After the jump break, output the full article body.

### Required pattern

```html
<article class="zv-blog-post">

  <img src="..." alt="...">

  <div class="post-intro">
    <p>
      A concise introduction describing what the article covers.
    </p>
  </div>

  <!--more-->

  <h2>First Main Section</h2>

  ...
</article>
```

---

## 5. Short Description / Intro Rules

The content inside:

```html
<div class="post-intro">
```

is the canonical short description for the post.

It is **not merely the first 100 characters** of the article.

It should be suitable for displaying in full on Blogger listing pages.

Normally use:

- one or two short paragraphs;
- approximately 60–180 words in total;
- enough context to tell the reader what the article covers;
- no unnecessary detail that belongs in the main article.

If the Markdown source already contains an obvious introductory section, use it.

Do not create a substantially new introduction unless explicitly requested.

If the source does not clearly separate an introduction from the article, use the opening paragraph or paragraphs that best function as the introduction.

The introduction must appear before `<!--more-->`.

---

## 6. Featured / Opening Image

When the Markdown begins with an article image, place that image before the `post-intro` section.

Example:

```html
<img
  src="https://example.com/image.png"
  alt="Descriptive image text">
```

Preserve the original image URL.

Always provide meaningful `alt` text when the source gives enough context to do so.

Do not:

- embed images as Base64;
- download and re-encode images;
- change image URLs unless explicitly requested;
- duplicate the featured image later in the article.

The Blogger theme separately displays the detected featured image on the single-post page. The theme contains logic to avoid duplicate rendering of the same first image.

---

## 7. Main Article

Everything after:

```html
<!--more-->
```

is the main article.

Preserve the Markdown hierarchy using semantic HTML:

| Markdown | HTML |
|---|---|
| `## Heading` | `<h2>` |
| `### Heading` | `<h3>` |
| `#### Heading` | `<h4>` |
| paragraph | `<p>` |
| unordered list | `<ul><li>...</li></ul>` |
| ordered list | `<ol><li>...</li></ol>` |
| inline code | `<code>` |
| code block | `<pre><code>...</code></pre>` |
| quote | `<blockquote>` |
| table | `<table>` |
| horizontal rule | `<hr>` |

Do not normally use `<h1>` inside the article because Blogger already renders the post title as the page-level `<h1>`.

Therefore:

- Markdown `# Title` should normally **not** be repeated inside the article body if it is the Blogger post title.
- Start article section headings at `<h2>`.

---

## 8. Code Blocks

Preserve code exactly.

Use:

```html
<pre><code>...</code></pre>
```

Escape HTML-significant characters inside code blocks when required:

- `&` → `&amp;`
- `<` → `&lt;`
- `>` → `&gt;`

Do not alter:

- SQL;
- PL/SQL;
- shell commands;
- Python;
- JSON;
- YAML;
- XML;
- configuration files;
- REST examples;
- command output.

Do not change quotation marks, capitalization, indentation, or syntax merely for stylistic reasons.

---

## 9. Inline Code

Use:

```html
<code>...</code>
```

for:

- commands;
- filenames;
- parameters;
- object names;
- schema names;
- table names;
- API endpoints;
- configuration properties;
- short code expressions.

---

## 10. Links

Convert Markdown links into normal anchors:

```html
<a href="https://example.com">Link text</a>
```

Preserve the original destination URL exactly unless explicitly asked to update it.

Do not add `target="_blank"` unless specifically requested.

---

## 11. Tables

Convert Markdown tables to semantic HTML:

```html
<table>
  <thead>
    <tr>
      <th>Column 1</th>
      <th>Column 2</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Value 1</td>
      <td>Value 2</td>
    </tr>
  </tbody>
</table>
```

Do not use inline styles.

---

## 12. Figures and Captions

If the Markdown clearly associates text as an image caption, use:

```html
<figure>
  <img src="..." alt="...">
  <figcaption>Caption text</figcaption>
</figure>
```

Otherwise a normal `<img>` is sufficient.

---

## 13. Special Content Blocks

If the source already uses custom semantic classes such as:

```html
<div class="analysis-block">
```

or other intentional custom blocks, preserve them unless explicitly instructed otherwise.

Do not invent large numbers of new CSS classes.

Prefer semantic HTML and the existing `.zv-blog-post` styling.

---

## 14. Blogger Structural Labels

The blog uses three Blogger labels with a structural purpose:

| Label | Purpose |
|---|---|
| `Posts` | Includes the article in the regular Posts index. |
| `Series` | Identifies a series overview / summary post and includes it in the Series index. |
| `Hero` | Makes the post eligible for the homepage Hero carousel. The latest three posts carrying this label are used by the carousel. |

These labels are **Blogger metadata**. They are assigned manually in Blogger and must **never be inserted into the generated HTML**.

Structural labels may be combined with normal topical labels.

For example, a regular article selected for the homepage Hero carousel might use:

```text
Posts, Hero, OPAF, MCP, Oracle Analytics
```

A series overview selected for the Hero carousel might use:

```text
Series, Hero, AI Data Platform
```

The `Hero` label does not change the HTML structure of the article. Hero selection and rendering are handled entirely by the Blogger theme.

---

## 15. Series and Regular Posts

A series overview post follows the same HTML structure as every other article.

If the post represents a **series overview**, assign the Blogger label:

```text
Series
```

The Series page lists posts carrying the `Series` label.

Inside a series overview post, preserve the complete list of series articles and links supplied in the Markdown.

A regular blog article should normally be assigned:

```text
Posts
```

Other topical labels may be assigned in Blogger as appropriate.

Do not place any Blogger labels inside the generated article HTML.

---

## 16. HTML Cleanliness

Generate clean HTML only.

Do not include:

```html
<html>
<head>
<body>
```

Do not include:

```html
<!DOCTYPE html>
```

Do not include metadata tags.

Do not include JavaScript unless the source explicitly requires JavaScript and the user has requested that it be retained.

Do not include CSS.

Do not include Blogger template tags such as:

```xml
<b:if>
<data:post.title/>
```

Those belong to the Blogger theme, not to post content.

---

## 17. Avoid Inline Styling

Do not generate:

```html
style="..."
```

unless absolutely required by source content and explicitly requested.

Formatting should be controlled centrally by `blogger-post.css` and the Blogger theme.

Prefer:

```html
<p>...</p>
```

over:

```html
<p style="font-size:16px;color:#123456">...</p>
```

---

## 18. Blogger Page-Weight Considerations

Long technical posts may contain many screenshots, code blocks, and large amounts of HTML.

Blogger uses automatic pagination and may reduce the number of posts displayed on an index page when posts are very large.

For this reason:

- always place the `<!--more-->` jump break immediately after the short description;
- keep the preview section compact;
- do not place multiple screenshots before `<!--more-->`;
- normally place only the featured image before the jump break;
- do not embed repeated CSS in the post;
- do not Base64-encode images.

The full article after `<!--more-->` may be as long and detailed as necessary.

---

## 19. Expected Output

Return only the Blogger-ready HTML unless the user asks for explanation.

The output should begin approximately with:

```html
<article class="zv-blog-post">
```

and end with:

```html
</article>
```

Do not wrap the HTML in a Markdown fenced code block when the user explicitly asks for content that will be copied directly into Blogger.

If a downloadable `.html` file is requested, create the file instead.

---

## 20. Example

Source concept:

```markdown
# Connecting OPAF to Oracle Analytics

![Architecture](image.png)

This article shows how Oracle Private Agent Factory can connect to Oracle Analytics Cloud using MCP.

It covers the architecture, configuration, and final integration.

## Architecture

The solution consists of...
```

Generated Blogger HTML:

```html
<article class="zv-blog-post">

  <img
    src="image.png"
    alt="OPAF and Oracle Analytics architecture">

  <div class="post-intro">
    <p>
      This article shows how Oracle Private Agent Factory can connect to
      Oracle Analytics Cloud using MCP.
    </p>
    <p>
      It covers the architecture, configuration, and final integration.
    </p>
  </div>

  <!--more-->

  <h2>Architecture</h2>

  <p>
    The solution consists of...
  </p>

</article>
```

---

## 21. Final Validation Checklist

Before returning the generated HTML, verify:

- [ ] Exactly one `<article class="zv-blog-post">` wrapper exists.
- [ ] No `<style>` block is embedded.
- [ ] No external CSS `<link>` is embedded in the post.
- [ ] No `<html>`, `<head>`, `<body>`, or `DOCTYPE` is included.
- [ ] Featured image is placed before the intro when one exists.
- [ ] Short description is wrapped in `<div class="post-intro">`.
- [ ] Exactly one `<!--more-->` exists.
- [ ] `<!--more-->` appears after the short description and before the main article.
- [ ] The Blogger post title is not unnecessarily repeated as `<h1>` inside the article.
- [ ] Main sections begin with `<h2>`.
- [ ] Code content has not been altered.
- [ ] Links and image URLs have been preserved.
- [ ] Images are not Base64 encoded.
- [ ] No unnecessary inline styles are present.
- [ ] Long article content remains after the jump break.
- [ ] No `Posts`, `Series`, `Hero`, or other Blogger labels have been inserted into the article HTML.
- [ ] The output is valid, clean HTML suitable for Blogger's HTML editor.

---

## Instruction to the AI

When these instructions are supplied together with a Markdown file, treat the Markdown file as the authoritative source content and these instructions as the authoritative formatting and Blogger publishing specification.

If the Markdown source conflicts with these formatting rules, preserve the source meaning but adapt its HTML structure to follow these Blogger rules.

If an ambiguity affects content rather than formatting, do not invent information. Preserve the source or ask for clarification when necessary.
