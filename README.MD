#名稱 線路檢查器

# 功能 自行載入.xml 後，再載入自訂規則.yaml後，執行檢查

## .xml 是由Allegro OrCAD 中的export to XML 功能產出，用來描述線路的情形

# 技術細節
使用vite8 做網頁介面，並結果python 做規則檢查
python 請用uv 管理環境，且使用3.12 

# 功能細節
## 規則 yaml產生器
可以設定元件名稱
* 在元件下可以設定很多條規則，例如 
    * pin1 需要接到1k ohm to gnd and 5.36kohms to Vcc.
    * pin2 跟Pin3之間需要放一個1ohm電阻
    * pin4 需要一個至少25V以上耐壓的電容，然後電容要求0.1uF 10% 以上


# 執行需求
等功能大致正常後，需打包成單一執行檔。之後執行後，使用者載入.xml檔跟.yaml檔後，就可以執行檢查了。