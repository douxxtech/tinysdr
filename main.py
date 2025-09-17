from components.app import App

if __name__ == "__main__":
    try:
        app = App()
        app.run()
    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
    except Exception as e:
        print(f"Fatal error: {e}")
