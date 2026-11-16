/**
 * AI Opportunity Scout -> Google Drive
 * Creates one Google Doc per AI idea in your folder, and appends build plans to it.
 *
 * Setup: Project Settings -> Script properties -> add SECRET = (any long random string, same as GDRIVE_WEBHOOK_SECRET)
 * Deploy -> New deployment -> Web app -> Execute as: Me, Who has access: Anyone -> copy the /exec URL.
 */
const DEFAULT_FOLDER_ID = '1WKKK2997P1i-mD9DmRHajuBJVt9Q8A4b';

function doPost(e) {
  const req = JSON.parse(e.postData.contents);
  const secret = PropertiesService.getScriptProperties().getProperty('SECRET');
  if (!secret || req.secret !== secret) return json_({ ok: false, error: 'unauthorised' });

  if (req.action === 'append' && req.docId) {
    const doc = DocumentApp.openById(req.docId);
    writeSections_(doc.getBody(), req.sections || []);
    doc.saveAndClose();
    return json_({ ok: true, docId: req.docId, url: doc.getUrl() });
  }

  const folder = DriveApp.getFolderById(req.folderId || DEFAULT_FOLDER_ID);
  const doc = DocumentApp.create(req.title || 'AI Idea');
  const body = doc.getBody();
  body.appendParagraph(req.title || 'AI Idea').setHeading(DocumentApp.ParagraphHeading.TITLE);
  if (req.subtitle) body.appendParagraph(req.subtitle).setHeading(DocumentApp.ParagraphHeading.SUBTITLE);
  writeSections_(body, req.sections || []);
  const first = body.getChild(0);
  if (first.getType() === DocumentApp.ElementType.PARAGRAPH && first.asParagraph().getText() === '') body.removeChild(first);
  doc.saveAndClose();

  const file = DriveApp.getFileById(doc.getId());
  file.moveTo(folder);
  return json_({ ok: true, docId: doc.getId(), url: doc.getUrl() });
}

function writeSections_(body, sections) {
  sections.forEach(function (s) {
    if (s.heading) body.appendParagraph(s.heading).setHeading(DocumentApp.ParagraphHeading.HEADING2);
    if (s.text) String(s.text).split('\n').forEach(function (line) { body.appendParagraph(line); });
    (s.bullets || []).forEach(function (b) {
      const li = body.appendListItem(String(b)).setGlyphType(DocumentApp.GlyphType.BULLET);
      if (b && /^https?:\/\//.test(String(b))) li.setLinkUrl(String(b));
    });
    (s.links || []).forEach(function (l) {
      const li = body.appendListItem(l.text || l.url).setGlyphType(DocumentApp.GlyphType.BULLET);
      if (l.url) li.setLinkUrl(l.url);
    });
  });
}

function json_(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}

/** Run once from the editor to grant Drive/Docs permissions and test the folder. */
function testSetup() {
  const f = DriveApp.getFolderById(DEFAULT_FOLDER_ID);
  Logger.log('Folder OK: ' + f.getName());
}
