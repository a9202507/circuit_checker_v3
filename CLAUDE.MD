#名稱 線路檢查器

# 功能 
用戶自行載入netlist.asc 跟 .BOM 後，再載入自訂規則.yaml後，可執行線路檢查

## .asc 是由Allegro OrCAD中，轉出netlist 頁面下，選擇pads2000的輸出格式
## .BOM 是由Allegro OrCAD中，產生出的 Bill of Material 表格

# 網頁需支持中英文介面切換，並且預設英文介面

# 在輸出結果頁面，需要有匯出完整報告的功能，完整報告包含：使用到的.asc , .bom, .yaml files 以及輸出report.html ，報告.html 檔名以namelist的名稱加上匯出日期，完整報告打包成.zip , 輸出報告.html請使用英文介面

# 技術細節
使用vite8 做網頁介面，並由python 做規則檢查
python 請用uv 管理環境，且使用3.12 

# 功能細節
## 規則 yaml產生器
以元件名稱命名 例如 XDPE1E496A.yaml 
* 在元件下可以設定很多條規則，
* XDPE1E496A.yaml 
    * 總pin數為53pin or 52pins ，若不符合則error. 
    * pin52 需接1uF cap to GND ，若不符合則warning.
    * pin52 需接0.1uF cap to GND，若不符合則warning.
    * pin51 需接1uF cap to GND ，若不符合則warning.
    * pin51 需接0.1uF cap to GND，若不符合則warning.
    * pin27 跟pin28 之間需要有一個220pF cap ，若不符合則error.

* TDM24544規則
    * pin16 需跟pin22 相連. 若不符合則error.
    * pin16 需接2.2uF to GND.若不符合則error.
    * pin38 需跟pin44 相連. 若不符合則error.
    * pin38 需接2.2uF to GND.若不符合則error.


# 執行需求
在UI環境下，設定那些loacation IC(U15/U16) 要使用那一個ruler.yaml來檢查。執行後，在UI上顯示每一條規則檢查結果