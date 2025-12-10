import flet as ft


def main(page: ft.Page):
    #カウンター表示用のテキスト
    counter = ft.Text("0", size=50, data=0)
    page.title = "Hello World"

    #ボタンが押された時に呼び出される関数
    def increment_click(e):
        counter.data += 1
        counter.value = str(counter.data)
        counter.update()
    #ボタンが押された時に呼び出される関数
    def decrement_click(e):
        counter.data -= 1
        counter.value = str(counter.data)
        counter.update()


#カウンターを増やすボタン
    page.floating_action_button = ft.FloatingActionButton(icon=ft.Icons.ADD, on_click=increment_click)
        #expand=Trueで、画面いっぱいに広げる
    page.add(
        ft.SafeArea(
            ft.Container(
                counter=ft.Row(countrols=[counter,hoge]),
                alignment=ft.alignment.center,
            ),
            expand=True,
        ),
        ft.FloatingActionButton(icon=ft.Icons.REMOVE, on_click=decrement_click)
    )


ft.app(main)
