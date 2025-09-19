RX_BG = (100, 000, 00, 255)
RX_FG = (245, 222, 179, 255)
RX_ACCENT = (242, 229, 218, 255)
RX_GREEN = (80, 200, 80, 255)
RX_RED = (255, 100, 100, 255)
RX_DIM = (145, 122, 79, 255)

TX_BG = (0, 0, 0, 255)
TX_FG = (230, 230, 230, 255)
TX_ACCENT = (200, 180, 150, 255)
TX_GREEN = (100, 220, 100, 255)
TX_RED = (255, 120, 120, 255)
TX_DIM = (180, 160, 130, 255)

def get_current_colors(mode):
        if mode == "RX":
            return {
                'bg': RX_BG,
                'fg': RX_FG,
                'accent': RX_ACCENT,
                'green': RX_GREEN,
                'red': RX_RED,
                'dim': RX_DIM
            }
        else:  # TX
            return {
                'bg': TX_BG,
                'fg': TX_FG,
                'accent': TX_ACCENT,
                'green': TX_GREEN,
                'red': TX_RED,
                'dim': TX_DIM
            }