import sys
from cli.main import ClockworkCLI
from config.settings import Settings
from state.state_manager import StateManager
from context.context_engine import ContextEngine

def main():
    settings = Settings.load()
    state    = StateManager(settings)
    context  = ContextEngine(state)
    cli      = ClockworkCLI(settings=settings, state=state, context=context)
    cli.run(sys.argv[1:])

if __name__ == "__main__":
    main()