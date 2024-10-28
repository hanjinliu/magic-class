from magicclass.widgets import Logger

def test_logger():
    log = Logger()
    log.print("Hello")
    log.print_table({"a": [1, 2], "b": [3, 4]})
    log.print_table([["a", "b"], [4, -1], [4.3, None]])
    log.print_html("<b>bold</b>")
    with log.set_stdout():
        print("Hello")
    with log.set_plt():
        import matplotlib.pyplot as plt
        plt.plot([1, 2, 3])
    log.clear()
