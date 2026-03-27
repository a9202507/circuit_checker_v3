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

* 其他規則種類
    * pin 需要空接(floating)
    * pin 需接到特定阻抗範圍之間的電阻到，且電阻器的另一端為特定netname(Vcc or gnd or others)
    * pin 需接到特定電容值範圍之間的電容，並且定義電容器的數量，且電容器的另一端為特定netname(Vcc or gnd or others)
    * pin 需接到特定電感感量範園之間的電感器，且電感器的另一端為特定netname(Vcc or gnd or others)
    * 多個pin 需要接在一起
    

# 執行需求
在UI環境下，設定那些loacation IC(U15/U16) 要使用那一個ruler.yaml來檢查。執行後，在UI上顯示每一條規則檢查結果

# Net 等效預處理（0Ω 電阻橋接）
系統在執行規則檢查前，會自動掃描 netlist 中所有 0Ω 電阻（值為 "0R"、"0"、"0ohm" 等）。若兩條 net 之間以 0Ω 電阻連接，則視為電氣等效（等同於直接相連）。

此等效關係支援多層串接（例如：NetA ← 0Ω ← NetB ← 0Ω ← NetC，則 A、B、C 均視為同一 net），並套用於所有規則類型：
* `pin_to_pin_connection`：pin1 與 pin2 透過 0Ω 橋接也視為相連
* `pin_to_gnd_cap`、`pin_to_net_capacitor` 等：capacitor 的另一端透過 0Ω 連到目標 net 也視為符合
* `pin_to_net_resistor`、`pin_to_net_inductor` 等：被動元件另一端透過 0Ω 連到目標 net 也視為符合

好處：設計者無需在 .asc netlist 中跨越 0Ω 電阻來定義網路連線，系統會自動視為等效。

# rail_name .spec 使用yaml格式
使用輸出電源名稱為檔名，此名稱需跟.asc中某一netname完全匹配。
內容包含 u16 , IC 料號 需對應netname 中的u16 以及BOM中 u16的料號
另外包含此電路的設計需求，例如Vout=1.8v, fsw=1.1Mhz , i2c address = n/a or 0x58 , FB voltage = digital or 0.7v , ocp = 14Amps , otp = 110C 等等 電路設計上的規格

# tda38806.spec 使用yaml格式
其中包含此IC各pin腳對應的變化
例如 TDA38806 pin6 fb voltage=0.6V 可用它及外部電阻回推輸出電壓是否符合rail_name.spec中的vout電壓規格。
例如 tda38806 pin12 mode pin ，接地電阻為 0ohm 時 此時為1.1Mhz 下的FCCM mode。30.1Kohms的話就是2Mhz的FCCM , 60.4Kohms就是600Khz FCCM