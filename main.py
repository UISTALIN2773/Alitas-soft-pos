from alitasbbq.config import init_ctk
from alitasbbq.db import init_database
from alitasbbq.app import AlitasBBQApp


def main():
    init_ctk()
    init_database()
    app = AlitasBBQApp()
    app.mainloop()


if __name__ == "__main__":
    main()

