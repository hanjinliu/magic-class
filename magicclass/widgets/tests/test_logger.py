from magicclass.widgets import Logger
import matplotlib.pyplot as plt

def test_logger():
    log = Logger()
    log.print("Hello")
    log.print_table({"a": [1, 2], "b": [3, 4]}, header=True)
    log.print_table({"a": [1, 2], "b": [3, 4]}, header=False)
    log.print_table([["a", "b"], [4, -1], [4.3, None]], header=True)
    log.print_table([["a", "b"], [4, -1], [4.3, None]], header=False)
    log.print_html("<b>bold</b>")
    with log.set_stdout():
        print("Hello")
    with log.set_plt():
        plt.plot([1, 2, 3])
    log.clear()
