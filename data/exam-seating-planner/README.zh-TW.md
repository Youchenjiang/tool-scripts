# 考場座位安排工具

[Read English Version](README.md)

安排考試座位，並產生考試時投影用的座位表。教室和考試都用 JSON 設定檔描述，換教室或換考試只要改設定檔，不用改程式。

## 功能特點

- **照實際教室格局**：方正的教室用「排數＋區塊」描述；不規則的教室（例如扇形階梯教室）直接讀 PowerPoint 畫好的平面圖，巢狀、旋轉的群組都能處理
- **精確的座位間隔**：左右一定不相鄰；優先減少斜角相鄰（斜前方的考卷看得到，正前方的會被那個人自己的身體擋住）；越靠近講台越好。逐排精確求解，不是隨機嘗試
- **座位規則**：指定某些學生在某間教室或某個座位；學號相鄰的人不坐在彼此周圍
- **獨立的規則檢查**：排完後逐條重新驗證，結果印在終端機
- **可直接投影**：每間教室一張 16:9 投影片，照實際方位畫，所有座位（空位較淡）都會畫出來，學生看得出自己在整間教室的哪裡；名字橫寫並自動調整大小
- **可重現**：考試設定裡的種子固定，每次執行結果都一樣

## 資料夾結構

```
exam-seating-planner/
├── src/
│   ├── seating.py      # 主程式
│   ├── rooms.py        # 讀取教室、判斷誰跟誰相鄰
│   ├── solver.py       # 第一階段：哪些位子坐人
│   ├── assign.py       # 第二階段：誰坐哪裡，以及規則檢查
│   ├── render.py       # 畫投影片
│   └── pptx_desks.py   # 從 PowerPoint 讀出桌子
├── rooms/              # 每間教室一個 JSON（309：方格型，404：從 PowerPoint 讀）
├── layouts/            # 教室設定引用的平面圖
├── exams/              # 範例考試設定
├── data.example/       # 範例用的虛構名單
├── data/               # [Git 忽略] 你的真實名單和考試設定
└── output/             # [Git 忽略] 產生的座位表
```

## 快速開始

```bash
pip install -r requirements.txt
python src/seating.py exams/example.json
```

範例會把 60 位虛構學生排進 309 和 404，並在 `output/` 產生兩個檔案：

- `<考試名稱>_<課名>_seating-chart.pptx`：投影給學生看的座位表。座位上是姓名和學號，其他文字只有教室名稱。規則檢查只印在終端機，不會在螢幕上公開個別學生的特殊安排。
- `<考試名稱>_<課名>_seat-layout-preview.pptx`：內部用。藍色是有人坐的位子，每張桌子都標有座位代號。

## 使用真實資料

真實名單和考試設定請放在 `data/`。這個資料夾已被 Git 忽略，不會被 commit。

1. 把名單（`.xlsx`）放進 `data/`。工作表格式不限，只要有一列是姓名和學號的欄位標題即可。
2. 把 `exams/example.json` 複製成 `data/<考試名稱>.json`，指向你的名單（路徑相對於設定檔本身）：
   ```json
   "roster": "roster.xlsx",
   "roster_columns": ["姓名", "學號"],
   "output": "../output"
   ```
3. 執行 `python src/seating.py data/<考試名稱>.json`。

## 教室設定

兩種寫法最後都會變成「一張張桌子的位置和角度」，再用同一套規則判斷相鄰。

**方格型**（`rooms/309.json`）

```json
{
  "name": "309",
  "type": "grid",
  "rows": 8,
  "blocks": [3, 3, 3],
  "blocked": [[8, 5]],
  "blocked_label": "Pillar",
  "podium": {"side": "top", "block": 2}
}
```

- `rows`：排數；`blocks`：每區幾列，區與區之間是走道
- `blocked`：不能坐的位置，寫 `[第幾排, 第幾列]`（從 1 開始，列數橫跨所有區）
- `podium`：講台在上方（`top`）或下方（`bottom`），對齊第幾區

**從 PowerPoint 讀**（`rooms/404.json`）

```json
{
  "name": "404",
  "type": "pptx",
  "file": "../layouts/room-404.pptx",
  "slide": 1,
  "podium_text": "講桌",
  "stretch_x": 1.1
}
```

- 投影片上文字是 `podium_text` 的那個方框是講台，其他每個方框都是一張桌子（可以放在群組裡、可以旋轉）
- 同一排的桌子要**緊貼**畫，程式靠這個判斷哪些桌子是同一排
- `stretch_x`：畫投影片時左右拉寬的倍數，只影響外觀

## 考試設定

```json
{
  "name": "example-midterm",
  "course": "EXAMPLE101",
  "roster": "../data.example/roster.example.xlsx",
  "roster_columns": ["Name", "ID"],
  "rooms": ["309", "404"],
  "counts": {},
  "fixed": {},
  "rules": {
    "room": {"404": ["Student 13", "Student 38"]},
    "seat": {"Student 13": "404 A1-1"},
    "id_apart": true
  },
  "labels": {"podium": "黑板", "blocked": "柱子", "rooms": {"309": "I1-309"}},
  "seed": 1,
  "output": "../output"
}
```

- `course`：課名，只用在輸出檔名，不會出現在投影片上
- `roster_columns`：名單裡姓名和學號的欄位標題
- `counts`：指定某間教室坐幾人，例如 `{"309": 36}`；沒寫的教室由程式決定
- `fixed`：指定某些位子一定要坐或一定空著，用座位代號，例如 `{"309": {"sit": ["B1-2"], "empty": ["B1-1", "B1-3"]}}`
- `rules.room`：指定某些人一定在某間教室
- `rules.seat`：指定某些人坐在某個座位，寫成 `"<教室> <座位代號>"`。程式會用交換的方式把他們換過去，其他人的位子不變；只有交換後違反規則時，才會整間重新排
- `rules.id_apart`：學號相鄰的兩人不能坐在彼此周圍
- `labels`（可省略）：投影片上的文字：`podium` 講台、`blocked` 不能坐的位置（例如柱子），以及 `rooms` 底下每間教室的標題；預設是 `Podium`、教室設定的 `blocked_label` 和 `Room <教室>`
- `seed`：其餘的人用這個數字打亂後排入；想換一組排法就改數字

## 座位代號

`區 排 - 位`，例如 `B1-2` 是 B 區第 1 排第 2 位。區照畫面由左到右是 A、B、C…，排從講台往後數，位由左到右。預覽檔上每張桌子都標有代號。

## 排座位的規則

**第一階段：哪些位子坐人**

1. 左右不相鄰（一定做到）
2. 斜角越少越好
3. 越靠近講台越好

相鄰關係由幾何位置判斷：同一排緊貼的是左右；往後一排最近的是前後，再旁邊一點的是斜角。每一區由前往後是一排接一排，所以可以逐排精確算出最佳解。

**第二階段：誰坐哪裡**（一定做到，做不到程式會直接報錯）

1. 指定教室（`rules.room`）和座位（`rules.seat`）
2. 學號相鄰的人不坐在彼此周圍（`rules.id_apart`）。「學號相鄰」是名單照學號排序後的前後一位；「周圍」包括前後、斜角、同一排隔一個空位，以及隔著走道的同一排

## 備註

- 投影片使用 Windows 內建的「微軟正黑體」來顯示中文姓名；其他系統的 PowerPoint 會自動替換字型
- 要列印或分享，最簡單的方式是用 PowerPoint 打開輸出的 `.pptx`，再匯出成 PDF 或圖片
