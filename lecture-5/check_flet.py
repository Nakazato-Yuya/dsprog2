import flet
import sys
import os

print("--------------------------------------------------")
print("【診断結果】")
print("--------------------------------------------------")

# 1. 読み込まれているFletのファイルの場所
# これが自分のフォルダ内のファイルを指していると、それが原因です。
print(f"1. Fletの読み込み元:\n   {flet.__file__}")

# 2. 使っているPython本体の場所
# これが .venv (仮想環境) の中か、Globalかを確認できます。
print(f"\n2. Pythonの実行パス:\n   {sys.executable}")

# 3. Fletの中に 'icons' という機能が入っているかチェック
if hasattr(flet, 'icons'):
    print("\n3. icons機能の状態:\n   ✅ 正常です（flet.icons は存在します）")
else:
    print("\n3. icons機能の状態:\n   ❌ エラーの原因です（flet.icons が見つかりません）")
    
    # 念のため、Fletの中に何が入っているかリストアップして表示
    print("\n   [Fletの中身一覧（一部）]")
    print(f"   {dir(flet)}")

print("--------------------------------------------------")
