import flet as ft
import requests
import sqlite3
import os

# -----------------------------------------------------------
# 定数定義
# -----------------------------------------------------------
AREA_URL = "http://www.jma.go.jp/bosai/common/const/area.json"
FORECAST_URL_BASE = "https://www.jma.go.jp/bosai/forecast/data/forecast/"
DB_NAME = "weather.db"

# 例外的なURL対応
URL_EXCEPTIONS = {
    "014030": "014100",  # 十勝 -> 釧路
    "460040": "460100",  # 奄美 -> 鹿児島
}

# -----------------------------------------------------------
# データベース処理（SQLite）
# -----------------------------------------------------------
def init_db():
    """DBとテーブルの初期化"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. エリア管理テーブル
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS areas (
            area_code TEXT PRIMARY KEY,
            area_name TEXT
        )
    """)
    
    # 2. 天気予報テーブル
    # area_code と target_date の組み合わせを一意(PK)とする
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS forecasts (
            area_code TEXT,
            target_date TEXT,
            weather_text TEXT,
            min_temp TEXT,
            max_temp TEXT,
            icon_name TEXT,
            PRIMARY KEY (area_code, target_date)
        )
    """)
    conn.commit()
    conn.close()

def save_area_to_db(code, name):
    """エリア情報をDBに保存"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # 重複していれば無視(INSERT OR IGNORE)
    cursor.execute("INSERT OR IGNORE INTO areas (area_code, area_name) VALUES (?, ?)", (code, name))
    conn.commit()
    conn.close()

def save_forecasts_to_db(area_code, forecast_list):
    """取得した予報リストをDBに保存（Upsert:あれば更新、なければ挿入）"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    for item in forecast_list:
        # REPLACE INTO は PKが重複する場合、古い行を削除して新しい行を入れる
        cursor.execute("""
            REPLACE INTO forecasts (area_code, target_date, weather_text, min_temp, max_temp, icon_name)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            area_code,
            item["date"],
            item["weather"],
            item["min"],
            item["max"],
            item["icon"]
        ))
    
    conn.commit()
    conn.close()

def get_forecasts_from_db(area_code):
    """DBから特定の地域の予報を取得する"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 日付順に取得
    cursor.execute("""
        SELECT target_date, weather_text, min_temp, max_temp, icon_name 
        FROM forecasts 
        WHERE area_code = ? 
        ORDER BY target_date ASC
    """, (area_code,))
    
    rows = cursor.fetchall()
    conn.close()
    
    # 辞書リストに変換して返す
    result = []
    for row in rows:
        result.append({
            "date": row[0],
            "weather": row[1],
            "min": row[2],
            "max": row[3],
            "icon": row[4]
        })
    return result

# -----------------------------------------------------------
# UI補助関数
# -----------------------------------------------------------
def get_weather_icon_info(text):
    """天気の文字からアイコンと色を決める"""
    # DB保存用にアイコン名を文字列で管理し、ここでFletのIconオブジェクトに変換する設計も可能だが
    # 今回は単純化のためロジックをそのまま使用
    if "晴" in text: return ft.Icons.WB_SUNNY, ft.Colors.ORANGE
    elif "雨" in text: return ft.Icons.UMBRELLA, ft.Colors.BLUE
    elif "曇" in text: return ft.Icons.CLOUD, ft.Colors.GREY
    elif "雪" in text: return ft.Icons.AC_UNIT, ft.Colors.CYAN
    else: return ft.Icons.WB_CLOUDY_OUTLINED, ft.Colors.GREY_400

def get_icon_name_for_db(text):
    """DB保存用に天気の文字列からアイコン識別子を返す（簡易実装）"""
    if "晴" in text: return "sunny"
    elif "雨" in text: return "rainy"
    elif "曇" in text: return "cloudy"
    elif "雪" in text: return "snowy"
    else: return "other"

# -----------------------------------------------------------
# メインアプリ
# -----------------------------------------------------------
def main(page: ft.Page):
    # アプリ起動時にDB初期化
    init_db()

    page.title = "天気予報アプリ (DB版)"
    page.padding = 0
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window_width = 1000
    page.window_height = 800
    
    page.appbar = ft.AppBar(
        leading=ft.Icon(ft.Icons.WB_SUNNY, color=ft.Colors.WHITE),
        title=ft.Text("天気予報 (SQLite連携)", color=ft.Colors.WHITE, weight="bold"),
        bgcolor=ft.Colors.INDIGO_900,
    )

    # UIパーツ
    weather_grid = ft.GridView(
        expand=True, runs_count=5, child_aspect_ratio=0.8,
        spacing=20, run_spacing=20, padding=20,
    )
    
    message_area = ft.Container(
        content=ft.Text("左のメニューから地域を選択してください", size=16, color=ft.Colors.GREY_700),
        alignment=ft.alignment.center, padding=20
    )

    main_content = ft.Container(
        content=ft.Column([message_area, weather_grid], expand=True),
        bgcolor=ft.Colors.BLUE_GREY_50, expand=True,
    )

    sidebar_column = ft.Column(scroll=ft.ScrollMode.ALWAYS, expand=True)
    sidebar = ft.Container(
        content=sidebar_column, width=280,
        bgcolor=ft.Colors.BLUE_GREY_800, padding=10,
    )

    # -------------------------------------------------------
    # ロジック：天気情報の取得・保存・表示
    # -------------------------------------------------------
    def display_weather(e):
        target_code = e.control.data
        region_name = e.control.title.value
        
        weather_grid.controls.clear()
        message_area.content = ft.Text(f"{region_name} のデータを更新中...", color=ft.Colors.BLACK)
        page.update()

        try:
            # 1. APIから最新データを取得
            file_code = URL_EXCEPTIONS.get(target_code, target_code)
            url = f"{FORECAST_URL_BASE}{file_code}.json"
            print(f"API Fetching: {url}") # Log

            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                
                # エリア特定
                time_series = data[0]["timeSeries"][0]
                dates = time_series["timeDefines"]
                
                target_area = None
                for area in time_series["areas"]:
                    if area["area"]["code"] == target_code:
                        target_area = area
                        break
                if target_area is None: target_area = time_series["areas"][0]

                weathers = target_area["weathers"]

                # 気温取得
                temps_min, temps_max = [], []
                try:
                    temp_series = data[0]["timeSeries"][1]
                    temp_area = temp_series["areas"][0]
                    temps_min = temp_area.get("tempsMin", [])
                    temps_max = temp_area.get("tempsMax", [])
                except: pass

                # 2. データを整形してリスト化
                forecast_data_list = []
                for i, (date_str, weather_text) in enumerate(zip(dates, weathers)):
                    date_val = date_str[:10]
                    min_t = temps_min[i] if i < len(temps_min) and temps_min[i] is not None else "-"
                    max_t = temps_max[i] if i < len(temps_max) and temps_max[i] is not None else "-"
                    icon_name = get_icon_name_for_db(weather_text)

                    forecast_data_list.append({
                        "date": date_val,
                        "weather": weather_text,
                        "min": min_t,
                        "max": max_t,
                        "icon": icon_name
                    })

                # 3. DBへ保存 (ここが今回の追加機能！)
                print(f"Saving to DB: {region_name} ({target_code})")
                save_forecasts_to_db(target_code, forecast_data_list)

            else:
                print("API Error, trying to load from DB...")

        except Exception as err:
            print(f"Update Error: {err}")
            # エラーが出ても、DBに古いデータがあればそれを表示するなどの工夫が可能

        # 4. DBからデータを読み込んで表示 (JSONから直接表示しない)
        # これにより「JSON -> DB -> View」の流れを実現
        db_forecasts = get_forecasts_from_db(target_code)
        
        if not db_forecasts:
            message_area.content = ft.Text("データの取得に失敗し、保存されたデータもありません。", color=ft.Colors.RED)
            page.update()
            return

        message_area.content = ft.Container() # メッセージ消去

        # カード作成 (DBのデータを使用)
        for item in db_forecasts:
            # DBから取り出した天気の文字を使ってアイコンを決める
            icon, icon_color = get_weather_icon_info(item["weather"])
            
            card = ft.Container(
                content=ft.Column(
                    [
                        ft.Text(item["date"], weight="bold", size=14),
                        ft.Icon(icon, size=48, color=icon_color),
                        ft.Text(item["weather"], size=12, text_align=ft.TextAlign.CENTER),
                        ft.Container(height=10),
                        ft.Row(
                            [
                                ft.Text(f"{item['min']}°C", color=ft.Colors.BLUE),
                                ft.Text(" / "),
                                ft.Text(f"{item['max']}°C", color=ft.Colors.RED),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER
                        )
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=5
                ),
                bgcolor=ft.Colors.WHITE, border_radius=10, padding=15,
                shadow=ft.BoxShadow(blur_radius=5, color=ft.Colors.GREY_300),
            )
            weather_grid.controls.append(card)
        
        page.update()

    # -------------------------------------------------------
    # 地域リスト読込
    # -------------------------------------------------------
    def load_area_list():
        try:
            print("地域リスト取得中...")
            response = requests.get(AREA_URL)
            data = response.json()
            
            sidebar_items = [
                ft.Text("地域を選択", color=ft.Colors.WHITE, weight="bold", size=16),
                ft.Divider(color=ft.Colors.GREY_600)
            ]

            for center in data["centers"].values():
                children_codes = center["children"]
                pref_tiles = []
                
                for code in children_codes:
                    if code in data["offices"]:
                        office = data["offices"][code]
                        name = office["name"]
                        
                        # (オプション) エリア情報をDBに保存
                        save_area_to_db(code, name)

                        tile = ft.ListTile(
                            title=ft.Text(name, color=ft.Colors.GREY_200, size=13),
                            data=code,
                            on_click=display_weather
                        )
                        pref_tiles.append(tile)
                
                if pref_tiles:
                    sidebar_items.append(
                        ft.ExpansionTile(
                            title=ft.Text(center["name"], color=ft.Colors.WHITE),
                            controls=pref_tiles,
                            icon_color=ft.Colors.WHITE,
                            collapsed_icon_color=ft.Colors.WHITE,
                            text_color=ft.Colors.WHITE,
                            collapsed_text_color=ft.Colors.WHITE
                        )
                    )
            
            sidebar_column.controls = sidebar_items
            page.update()
            print("リスト作成完了")

        except Exception as err:
            sidebar_column.controls.append(ft.Text(f"リスト読込失敗: {err}", color="red"))
            page.update()

    # アプリ構築
    page.add(ft.Row([sidebar, main_content], expand=True, spacing=0))
    load_area_list()

ft.app(target=main)