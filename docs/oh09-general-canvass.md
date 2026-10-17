# 2022 OH-09：州認証済み8郡のGeneral票とFECの独立照合（Issue #17）

検証日: **2026-10-17**。資料の範囲: **2022年11月8日General Electionのみ**（May 3rd Primaryは別件・未検証）。

## Ohio選管の公式一次資料

[Lucas County Board of Electionsが第9区の最多人口郡として認証した8郡の公式canvass（Defiance County BOE保管）](https://www.boe.ohio.gov/defiance/c/elecres/20221108overlap.pdf)には、州内8郡の下院第9区票と**地区全体の合計**が記録されている。[Defiance County公式確定結果](https://www.boe.ohio.gov/defiance/c/elecres/20221108results.pdf)の候補者得票も同表のDefiance郡部分に一致。[Ohio Secretary of Stateの2022年本選挙認証公表](https://www.ohiosos.gov/office/media-center/categories/press-releases/2022-12-09)は州全体の認証日が12月9日であることを裏付ける。

| 2022年General：郡 | Marcy Kaptur（D） | J.R. Majewski（R） |
|---|---:|---:|
| Defiance | 5,272 | 7,914 |
| Erie | 15,249 | 13,498 |
| Fulton | 6,544 | 9,584 |
| Lucas | 86,676 | 44,972 |
| Ottawa | 8,906 | 9,400 |
| Sandusky | 9,523 | 11,607 |
| Williams | 4,732 | 7,947 |
| Wood | 13,753 | 10,440 |
| **8郡総計** | **150,655** | **115,362** |

公式canvassの地区合計は**Kaptur D=150,655、Majewski R=115,362**。上記の8郡を再合計しても同じ数字となり、[FEC公式2022年ExcelのOH-09](../data/sources/fec_publications.json)に記録されたGeneral D=150,655／R=115,362と独立一致する。

- **認証結果として独立に確認できたのはGeneralのみ**。FEC原票から抽出したPrimary D=32,968、R=61,090および共和党Primary4候補の票数は今回のOhio canvvassには含まれない。これらがOhio州公式Primary票と一致するかは別に検証する。
- Generalで民主党が共和党より35,293票多かったという算術は確認できる。しかし予測誤差の原因（党内競争、候補者個人の支持、制度、地域情勢）は**この確定結果だけでは断定できない**。
- 8郡の票と公表合計は公式PDFから事前に転記したJSONであり、**CIはOhio州の原PDFを毎回取得・解析しない**。FEC2022 ExcelはCIが再取得し、正規化結果と州の転記値を再比較する。データの版・原典・検証対象を分けて記録する。

## 再現コード

- [公式certified canvassから転記した郡別票とURL](../data/sources/oh09_2022_official_general_canvass.json)
- [8郡の候補者票合計とFEC General票を比較](../scripts/verify_oh09_general_canvass.py)
- [郡欠損・転記ミス・不正な「Primary照合済み」フラグ等の回帰テスト](../tests/test_oh09_general_canvass.py)

    python scripts/download_fec.py --years 2022
    python scripts/normalize_fec.py --years 2022
    python scripts/verify_oh09_general_canvass.py

研究用の916件の選択基準、モデル指標は変更しない。**Issue #17はGeneralのみ検証完了、Primary公式結果は未完了としてOpenを維持**する。
