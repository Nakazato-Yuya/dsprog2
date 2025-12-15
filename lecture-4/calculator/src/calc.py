import flet as ft
import math

class CalcButton(ft.ElevatedButton):
    def __init__(self, text, button_clicked, expand=1):
        super().__init__()
        self.text = text
        self.expand = expand
        self.on_click = button_clicked
        self.data = text

class DigitButton(CalcButton):
    def __init__(self, text, button_clicked, expand=1):
        CalcButton.__init__(self, text, button_clicked, expand)
        self.bgcolor = ft.Colors.WHITE24
        self.color = ft.Colors.WHITE

class ActionButton(CalcButton):
    def __init__(self, text, button_clicked):
        CalcButton.__init__(self, text, button_clicked)
        self.bgcolor = ft.Colors.ORANGE
        self.color = ft.Colors.WHITE

class ExtraActionButton(CalcButton):
    def __init__(self, text, button_clicked):
        CalcButton.__init__(self, text, button_clicked)
        self.bgcolor = ft.Colors.BLUE_GREY_100
        self.color = ft.Colors.BLACK

# 新しく追加: 科学計算用ボタンのデザイン（少し暗めの色に設定）
class ScientificButton(CalcButton):
    def __init__(self, text, button_clicked):
        CalcButton.__init__(self, text, button_clicked)
        self.bgcolor = ft.Colors.INDIGO_400
        self.color = ft.Colors.WHITE

class CalculatorApp(ft.Container):
    def __init__(self):
        super().__init__()
        self.reset()

        self.result = ft.Text(value="0", color=ft.Colors.WHITE, size=20)
        self.width = 400 # ボタンが増えたので少し幅を広げる
        self.bgcolor = ft.Colors.BLACK
        self.border_radius = ft.border_radius.all(20)
        self.padding = 20
        self.content = ft.Column(
            controls=[
                ft.Row(controls=[self.result], alignment="end"),
                # 科学計算ボタンの行を追加
                ft.Row(
                    controls=[
                        ScientificButton(text="sin", button_clicked=self.button_clicked),
                        ScientificButton(text="cos", button_clicked=self.button_clicked),
                        ScientificButton(text="tan", button_clicked=self.button_clicked),
                        ScientificButton(text="log", button_clicked=self.button_clicked),
                    ]
                ),
                # もう一行追加（平方根と2乗）
                ft.Row(
                    controls=[
                        ScientificButton(text="sqrt", button_clicked=self.button_clicked),
                        ScientificButton(text="x^2", button_clicked=self.button_clicked),
                        # レイアウト調整のため空のコンテナや既存機能を入れることも可能だが、
                        # ここでは元の機能の一部を配置調整しても良い
                        ExtraActionButton(text="(", button_clicked=self.button_clicked), # 実装は省略(Errorになる)または保留
                        ExtraActionButton(text=")", button_clicked=self.button_clicked), # レイアウト埋め
                    ]
                ),
                ft.Row(
                    controls=[
                        ExtraActionButton(text="AC", button_clicked=self.button_clicked),
                        ExtraActionButton(text="+/-", button_clicked=self.button_clicked),
                        ExtraActionButton(text="%", button_clicked=self.button_clicked),
                        ActionButton(text="/", button_clicked=self.button_clicked),
                    ]
                ),
                ft.Row(
                    controls=[
                        DigitButton(text="7", button_clicked=self.button_clicked),
                        DigitButton(text="8", button_clicked=self.button_clicked),
                        DigitButton(text="9", button_clicked=self.button_clicked),
                        ActionButton(text="*", button_clicked=self.button_clicked),
                    ]
                ),
                ft.Row(
                    controls=[
                        DigitButton(text="4", button_clicked=self.button_clicked),
                        DigitButton(text="5", button_clicked=self.button_clicked),
                        DigitButton(text="6", button_clicked=self.button_clicked),
                        ActionButton(text="-", button_clicked=self.button_clicked),
                    ]
                ),
                ft.Row(
                    controls=[
                        DigitButton(text="1", button_clicked=self.button_clicked),
                        DigitButton(text="2", button_clicked=self.button_clicked),
                        DigitButton(text="3", button_clicked=self.button_clicked),
                        ActionButton(text="+", button_clicked=self.button_clicked),
                    ]
                ),
                ft.Row(
                    controls=[
                        DigitButton(text="0", expand=2, button_clicked=self.button_clicked),
                        DigitButton(text=".", button_clicked=self.button_clicked),
                        ActionButton(text="=", button_clicked=self.button_clicked),
                    ]
                ),
            ]
        )

    def button_clicked(self, e):
        data = e.control.data
        print(f"Button clicked with data = {data}")
        
        # エラー状態からの復帰
        if self.result.value == "Error" and data != "AC":
             self.result.value = "0"
             self.reset()
             
        if data == "AC":
            self.result.value = "0"
            self.reset()

        elif data in ("1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "."):
            if self.result.value == "0" or self.new_operand == True:
                self.result.value = data
                self.new_operand = False
            else:
                self.result.value = self.result.value + data

        elif data in ("+", "-", "*", "/"):
            self.result.value = self.calculate(self.operand1, float(self.result.value), self.operator)
            self.operator = data
            if self.result.value == "Error":
                self.operand1 = "0"
            else:
                self.operand1 = float(self.result.value)
            self.new_operand = True

        elif data in ("="):
            self.result.value = self.calculate(self.operand1, float(self.result.value), self.operator)
            self.reset()

        elif data in ("%"):
            self.result.value = float(self.result.value) / 100
            self.reset()

        elif data in ("+/-"):
            if float(self.result.value) > 0:
                self.result.value = "-" + str(self.result.value)
            elif float(self.result.value) < 0:
                self.result.value = str(self.format_number(abs(float(self.result.value))))

        # --- 科学計算ロジックの追加 ---
        elif data in ("sin", "cos", "tan", "log", "sqrt", "x^2"):
            try:
                val = float(self.result.value)
                if data == "sin":
                    # math.sinはラジアンを受け取るためそのまま使用
                    res = math.sin(val)
                elif data == "cos":
                    res = math.cos(val)
                elif data == "tan":
                    res = math.tan(val)
                elif data == "log":
                    # 自然対数。0以下はエラー
                    if val <= 0:
                        res = "Error"
                    else:
                        res = math.log(val)
                elif data == "sqrt":
                    # 平方根。負の数はエラー
                    if val < 0:
                        res = "Error"
                    else:
                        res = math.sqrt(val)
                elif data == "x^2":
                    res = math.pow(val, 2)
                
                if res != "Error":
                    self.result.value = str(self.format_number(res))
                else:
                    self.result.value = "Error"
                    
                self.new_operand = True
                
            except Exception as e:
                print(e)
                self.result.value = "Error"
        
        # レイアウト埋め用の未実装ボタン
        elif data in ("(", ")"):
            pass # 今回は未実装

        self.update()

    def format_number(self, num):
        try:
            if num % 1 == 0:
                return int(num)
            else:
                return round(num, 6) # 小数点以下が長くなりすぎないように丸める
        except:
            return num

    def calculate(self, operand1, operand2, operator):
        try:
            if operator == "+":
                return self.format_number(operand1 + operand2)
            elif operator == "-":
                return self.format_number(operand1 - operand2)
            elif operator == "*":
                return self.format_number(operand1 * operand2)
            elif operator == "/":
                if operand2 == 0:
                    return "Error"
                else:
                    return self.format_number(operand1 / operand2)
        except:
            return "Error"

    def reset(self):
        self.operator = "+"
        self.operand1 = 0
        self.new_operand = True

def main(page: ft.Page):
    page.title = "Scientific Calculator"
    calc = CalculatorApp()
    page.add(calc)

ft.app(main)