# Bible Concordance | קונקורדנציה לתנ״ך

🌐 **האתר (GitHub Pages):** https://elfifo4.github.io/bible-concordance/

An open, Hebrew-first concordance of the Hebrew Bible, designed for precise word lookup, grammatical analysis, and navigation to every occurrence in the biblical text.

> **Status (2026-11-25):** all 22 letters are generated from the pinned MorphHB and HebrewLexicon revisions (9,241 entries, 299,536 occurrences); every entry has a Hebrew gloss draft with byte-exact Strong and BDB excerpts, and every occurrence is audited against the source. **No entry is editorially approved yet.** Per-letter status: [docs/STATUS.md](docs/STATUS.md). Tooling: `scripts/concordance.py` (see `python3 scripts/concordance.py --help`).
>
> **מצב (25.11.2026):** כל 22 האותיות נוצרו מגרסאות המקור המקובעות; לכל ערך טיוטת פירוש עברי וקטעי Strong ו-BDB מאומתים. **אף ערך טרם אושר עריכתית.**

## מטרת הפרויקט

יצירת קונקורדנציה דיגיטלית לתנ״ך, עם ממשק עברי ומאגר נתונים פתוח וניתן לשימוש חוזר.

המערכת מיועדת לאפשר:
- עיון בערכים מילוניים לפי אותיות א׳–ת׳, לרבות מילים נפוצות, שמות פרטיים ושורשים.
- הצגת **צורת יסוד מילונית** גם כאשר המילה מופיעה במקרא רק בצורת נטייה או רבים.
- הגדרות **בעברית**, מחולקות למשמעויות נפרדות.
- הצגת כל ההיקרויות של כל ערך, עם הפניה מדויקת לספר, פרק, פסוק ומיקום המילה.
- שיוך כל היקרות למשמעות המתאימה לה בהקשר הפסוק, ככל שניתן לקבוע זאת.
- מידע מורפולוגי ודקדוקי, חיפוש לפי ערך, שורש וצורה מנוקדת או בלתי מנוקדת.
- שימוש באותם נתונים באתר ובאפליקציות, לרבות שמירה מקומית לעבודה ללא אינטרנט.

## עקרונות מידול

1. **ערך מילוני אינו שורש:** צורת היסוד (lemma/headword) והשורש (root) נשמרים בנפרד.
2. **נטיות אינן ערכים עצמאיים בהכרח:** תחיליות כגון ו׳ החיבור, ה׳ הידיעה וסיומות נטייה מקושרות לערך היסוד.
3. **הבחנה בין משמעויות:** לכל ערך יכולות להיות מספר משמעויות (`senses`); כל היקרות יכולה להצביע על `senseId` מסוים.
4. **אי־ודאות מתועדת:** כאשר לא ניתן לקבוע משמעות בביטחון, `senseId` יכול להיות `null`; סיווג אוטומטי אינו שקול לאימות אנושי.
5. **ללא שכפול טקסט:** פסוקים, ערכים והיקרויות נשמרים במבנים נפרדים עם מזהים יציבים.
6. **ייחוס מקורות ובקרה:** יש לתעד את מקור הנתונים, שיטת הסיווג וסטטוס הבדיקה.

## מקורות נתונים מוצעים

- [Open Scriptures MorphHB](https://github.com/openscriptures/morphhb) — טקסט עברי של התנ״ך ומידע מורפולוגי.
- [Open Scriptures Hebrew Lexicon](https://github.com/openscriptures/HebrewLexicon) — נתונים מילוניים וקישורים למערכות כגון Strong ו־BDB.

**חשוב:** יש לבדוק את הרישיונות של כל מקור ושל כל רכיב נתונים לפני ייבוא או הפצה. הגדרות בעברית ייכתבו באופן מקורי או יילקחו ממקורות בעלי רישיון מתאים; אין להעתיק הגדרות מוגנות מקונקורדנציות מסחריות.

## מבנה נתונים מתוכנן

```text
data/
  entries/           # רשימות ערכים לפי אות
  occurrences/       # היקרויות לפי מזהה ערך
  verses/            # טקסט הפסוקים
  index.json         # מטא־דאטה ואינדקסים
schemas/             # JSON Schema
scripts/             # ייבוא, נרמול, בנייה ואימות
docs/                # אפיון, מקורות והחלטות
```

המבנה הזה הוא **תכנון ראשוני**, לא התחייבות לשמות קבצים סופיים.

### דוגמה רעיונית — ערך

```json
{
  "id": "heb-eretz",
  "headword": "אֶרֶץ",
  "headwordUnpointed": "ארץ",
  "letter": "א",
  "type": "word",
  "root": null,
  "senses": [
    { "id": "land", "definition": "שטח יבשה או חבל ארץ" }
  ],
  "reviewStatus": "pending"
}
```

### דוגמה רעיונית — היקרות

```json
{
  "tokenId": "example-token-id",
  "entryId": "heb-eretz",
  "verseId": "GEN.1.10",
  "senseId": null,
  "classificationMethod": "unclassified",
  "reviewStatus": "pending"
}
```

הדוגמאות להמחשת המבנה בלבד; הן אינן רשומות מיובאות או מסווגות ממאגר התנ״ך.

## אחסון והפצה

ה־GitHub repository הוא מקור האמת של הנתונים והקוד. בשלב ראשון אפשר להפיץ קובצי JSON סטטיים ישירות ממנו, תוך שימוש בגרסאות קבועות ובמטמון מקומי באפליקציה. אם בעתיד יהיה צורך, ניתן להעביר את קובצי ההפצה לאחסון סטטי או CDN ייעודי ללא שינוי עקרוני במודל הנתונים.

**ייצוא לאפליקציה:** `python3 scripts/concordance.py export-app` כותב שני קבצים קטנים (כ-2 MB, כ-1 MB דחוס) שאפליקציית "הראשון בחידון" מצרפת ועובדת איתם בלי אינטרנט, במיקומי המילים של טקסט התנ״ך שלה עצמה. פירוט: [docs/APP_EXPORT.md](docs/APP_EXPORT.md).

רשימות ארוכות יוצגו באמצעות גלילה וירטואלית; היקרויות רבות יוצגו בהדרגה (pagination בצד הלקוח בשלב ראשון).

## אבני דרך

1. הגדרת JSON Schema ומזהים יציבים.
2. בדיקת רישיונות, גרסאות ומידת הכיסוי של מקורות הנתונים.
3. ייבוא הטקסט והמורפולוגיה ויצירת אינדקס היקרויות.
4. יצירת ערכים מילוניים, צורות נטייה והגדרות בעברית.
5. סיווג היקרויות לפי משמעות עם רמת ביטחון וסטטוס סקירה.
6. בדיקות שלמות, עקביות וקישוריות בין כל הרשומות.
7. בניית חבילות JSON להפצה וצריכה באפליקציות.

## איכות נתונים

המטרה היא כיסוי מלא של מילות התנ״ך, אך **אין להניח שכיסוי מילוני, ניתוח מורפולוגי וסיווג סמנטי הושלמו או אומתו** עד שיופקו דוחות בדיקה מתאימים. כל רשומה שמצריכה הכרעה לשונית תישאר מסומנת לבדיקה.

## License

Original concordance data and original documentation are licensed under **[Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/)**. Commercial use (including ad-supported apps) is permitted subject to attribution and other license conditions.

See [LICENSE](LICENSE) and [ATTRIBUTION.md](ATTRIBUTION.md). Third-party sources retain their own licenses; verify each component before importing or distributing it. Future software scripts may use a separate MIT license when explicitly marked.
