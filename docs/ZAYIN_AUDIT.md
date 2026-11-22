# אות ז׳ — מצב מילון ובדיקות (22.11.2026)

- **169 ערכים מילוניים** ו־**4,505 היקרויות** בקובץ `data/alphabet/ז.json`.
- נכתבו **169 פירושים עבריים ראשוניים** בקובץ `data/zayin-hebrew-drafts.txt` ושולבו בכל הערכים.
- **אין אישור עריכתי** לפירושים. בחלק מהערכים הנדירים יש משמעות מסופקת, והניסוחים דורשים הצלבה פרטנית מול המקורות.
- נוצר סקריפט `scripts/build-zayin-dictionary.cjs` המבוסס על תהליך האות ה׳, שמטרתו להצליב Strong, BDB ו־MorphHB מול גרסאות המקור המקובעות ולתקן מיקומי טוקנים במידת הצורך.
- **הסקריפט טרם הורץ בהצלחה**: אין לסמן בדיקת Strong/BDB או אימות 4,505 הטוקנים כעובדה שהושלמה. השדות `strongSourceChecked`, `bdbSourceChecked`, `occurrenceCountChecked`, `editoriallyApproved` נשארו `false`.
- לפי החלטת העבודה, יש להריץ את הבדיקות **מקומית במקבוק דרך Claude Code**, ולא להפעיל GitHub Actions אוטומטית.

## פקודות להרצה מקומית

```bash
node scripts/build-zayin-dictionary.cjs
node tests/vav-definitions.test.cjs
python3 -m unittest discover -s tests -v
```

לאחר ההרצה יש לבדוק חריגים ב־LexicalIndex/BDB, לתעד תוצאות, ולהשלים בקרת פירושים עבריים. אין להציג את הטיוטות כמאושרות עד לכך.
