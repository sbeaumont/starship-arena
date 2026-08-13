// The little markdown the write-ups in Valhalla are written in: headings, bold, italic, lists and
// paragraphs. Everything is escaped before a rule runs, so markup somebody types is text a reader
// sees, and nothing anyone writes reaches the page as markup of its own.

const ESCAPED = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }

const HEADING = /^(#{1,3})\s+(.*)$/
const BULLET = /^[-*]\s+(.*)$/
const NUMBERED = /^\d+[.)]\s+(.*)$/

const inline = (text) =>
  text
    .replace(/[&<>"]/g, (c) => ESCAPED[c])
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
    .replace(/_([^_]+)_/g, '<em>$1</em>')

export function render(text) {
  const out = []
  let paragraph = []
  let list = null

  const closeParagraph = () => {
    if (paragraph.length) out.push(`<p>${inline(paragraph.join(' '))}</p>`)
    paragraph = []
  }
  const closeList = () => {
    if (list) out.push(`</${list}>`)
    list = null
  }
  const openList = (kind) => {
    if (list === kind) return
    closeList()
    out.push(`<${kind}>`)
    list = kind
  }

  for (const raw of text.split(/\r?\n/)) {
    const line = raw.trim()
    const heading = HEADING.exec(line)
    const item = BULLET.exec(line) || NUMBERED.exec(line)
    if (!line) {
      closeParagraph()
      closeList()
    } else if (heading) {
      closeParagraph()
      closeList()
      // The page owns h1 and h2, so what a writer calls a heading starts below them.
      const level = heading[1].length + 2
      out.push(`<h${level}>${inline(heading[2])}</h${level}>`)
    } else if (item) {
      closeParagraph()
      openList(BULLET.test(line) ? 'ul' : 'ol')
      out.push(`<li>${inline(item[1])}</li>`)
    } else {
      closeList()
      paragraph.push(line)
    }
  }
  closeParagraph()
  closeList()
  return out.join('')
}