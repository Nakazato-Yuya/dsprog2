import flet as ft
import requests

# -----------------------------------------------------------
# 定数定義（APIのURLなど）
# -----------------------------------------------------------
AREA_URL = "http://www.jma.go.jp/bosai/common/const/area.json"
FORECAST_URL_BASE = "https://www.jma.go.jp/bosai/forecast/data/forecast/"

# 天気の文字からアイコンと色を決める補助関数
def get_weather_icon_info(text):
    if "晴" in text:
        return ft.Icons.WB_SUNNY, ft.Colors.ORANGE
    elif "雨" in text:
        return ft.Icons.UMBRELLA, ft.Colors.BLUE
    elif "曇" in text:
        return ft.Icons.CLOUD, ft.Colors.GREY
    elif "雪" in text:
        return ft.Icons.AC_UNIT, ft.Colors.CYAN
    else:
        return ft.Icons.WB_CLOUDY_OUTLINED, ft.Colors.GREY_400

def main(page: ft.Page):
    # -------------------------------------------------------
    # 1. アプリの基本設定
    # -------------------------------------------------------
    page.title = "天気予報アプリ"
    page.padding = 0
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window_width = 1200
    page.window_height = 800
    
    # アプリ上部のバー（紺色）
    page.appbar = ft.AppBar(
        leading=ft.Icon(ft.Icons.WB_SUNNY, color=ft.Colors.WHITE),
        title=ft.Text("天気予報", color=ft.Colors.WHITE, weight="bold"),
        bgcolor=ft.Colors.INDIGO_900,
    )

    # -------------------------------------------------------
    # 2. 画面パーツ（枠組み）の作成
    # -------------------------------------------------------
    
    # 右側：天気カードを並べるエリア（最初は空っぽ）
    weather_grid = ft.GridView(
        expand=True,
        runs_count=5,           # 横に並べる最大数
        child_aspect_ratio=0.8, # カードの縦横比
        spacing=20,             # カード間の隙間
        run_spacing=20,
        padding=20,
    )
    
    # 右側：メッセージ表示エリア
    message_area = ft.Container(
        content=ft.Text("左のメニューから地域を選択してください", size=16, color=ft.Colors.GREY_700),
        alignment=ft.alignment.center,
        expand=True
    )

    # 右側全体（背景色つき）
    main_content = ft.Container(
        content=ft.Column([message_area, weather_grid], expand=True),
        bgcolor=ft.Colors.BLUE_GREY_50,
        expand=True,
    )

    # 左側：サイドバーの中身（最初は空っぽ）
    sidebar_column = ft.Column(scroll=ft.ScrollMode.AUTO)
    
    # 左側全体（背景色つき）
    sidebar = ft.Container(
        content=sidebar_column,
        width=250,
        bgcolor=ft.Colors.BLUE_GREY_800,
        padding=10,
    )

    # -------------------------------------------------------
    # 3. ロジック（動き）の定義
    # -------------------------------------------------------

    # 【機能A】選択された地域の天気を取得して表示する
    def display_weather(e):
        # ボタンから地域コードと名前を取り出す
        code = e.control.data
        region_name = e.control.title.value
        
        # 画面をリセットして読み込み中にする
        weather_grid.controls.clear()
        message_area.content = ft.Text(f"{region_name}のデータを取得中...", color=ft.Colors.BLACK)
        page.update()

        try:
            # APIからデータを取得
            url = f"{FORECAST_URL_BASE}{code}.json"
            response = requests.get(url)
            data = response.json()

            # --- JSON解析 ---
            # data[0] -> timeSeries[0] (天気) -> areas[0] (該当地域) -> weathers (天気リスト)
            time_series = data[0]["timeSeries"][0]
            dates = time_series["timeDefines"]
            
            # 地域コードが一致するエリアを探す
            target_area = next((a for a in time_series["areas"] if a["area"]["code"] == code), time_series["areas"][0])
            weathers = target_area["weathers"]

            # 気温データの取得（エラー回避のためtry使用）
            temps_min, temps_max = [], []
            try:
                temp_area = data[0]["timeSeries"][1]["areas"][0]
                temps_min = temp_area.get("tempsMin", [])
                temps_max = temp_area.get("tempsMax", [])
            except:
                pass # 気温が取れなくても無視して進む

            # 準備完了：メッセージを消す
            message_area.content = ft.Container()
            
            # 日付と天気を組み合わせてカードを作る
            for i, (date_str, weather_text) in enumerate(zip(dates, weathers)):
                date_val = date_str[:10] # 日付だけ切り出し
                icon, icon_color = get_weather_icon_info(weather_text)
                
                # 気温テキスト（データがある場合のみ表示）
                min_t = temps_min[i] if i < len(temps_min) and temps_min[i] != "" else "-"
                max_t = temps_max[i] if i < len(temps_max) and temps_max[i] != "" else "-"
                
                # カードの中身を作成
                card = ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(date_val, weight="bold"),
                            ft.Icon(icon, size=48, color=icon_color),
                            ft.Text(weather_text, size=12, text_align=ft.TextAlign.CENTER),
                            ft.Row(
                                [
                                    ft.Text(f"{min_t}°C", color=ft.Colors.BLUE),
                                    ft.Text(" / "),
                                    ft.Text(f"{max_t}°C", color=ft.Colors.RED),
                                ], 
                                alignment=ft.MainAxisAlignment.CENTER
                            )
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER
                    ),
                    bgcolor=ft.Colors.WHITE,
                    border_radius=10,
                    padding=15,
                    shadow=ft.BoxShadow(blur_radius=5, color=ft.Colors.GREY_300),
                )
                weather_grid.controls.append(card)

        except Exception as err:
            message_area.content = ft.Text(f"エラーが発生しました: {err}", color=ft.Colors.RED)
        
        page.update()

    # 【機能B】起動時に地域リストを読み込んでサイドバーを作る
    def load_area_list():
        try:
            response = requests.get(AREA_URL)
            data = response.json()
            
            # サイドバーの見出し
            sidebar_items = [
                ft.Text("地域を選択", color=ft.Colors.WHITE, weight="bold"),
                ft.Divider(color=ft.Colors.GREY_600)
            ]

            # 地方ごとにループ
            for center in data["centers"].values():
                children_codes = center["children"]
                pref_tiles = []
                
                # 都道府県ごとにループ
                for code in children_codes:
                    if code in data["offices"]:
                        office = data["offices"][code]
                        # ボタンを作成（ここにコードを隠し持つ）
                        tile = ft.ListTile(
                            title=ft.Text(office["name"], color=ft.Colors.GREY_300, size=13),
                            data=code, # 重要：クリック時にこれを使う
                            on_click=display_weather
                        )
                        pref_tiles.append(tile)
                
                # 折りたたみメニューに追加
                if pref_tiles:
                    sidebar_items.append(
                        ft.ExpansionTile(
                            title=ft.Text(center["name"], color=ft.Colors.WHITE),
                            controls=pref_tiles,
                            icon_color=ft.Colors.WHITE,
                            collapsed_icon_color=ft.Colors.WHITE
                        )
                    )
            
            sidebar_column.controls = sidebar_items
            page.update()

        except Exception as err:
            sidebar_column.controls.append(ft.Text(f"リスト読込エラー: {err}", color="red"))
            page.update()

    # -------------------------------------------------------
    # 4. 画面の組み立てと起動
    # -------------------------------------------------------
    # 左（サイドバー）と右（メイン）を横並びにする
    page.add(
        ft.Row(
            [sidebar, main_content],
            expand=True,
            spacing=0
        )
    )

    # 最後にリスト読み込みを実行
    load_area_list()

ft.app(target=main)