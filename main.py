import gc                      # Garbage collection
import time                    # Time functions
import asyncio                 # Asynchronous I/O
import traceback               # Exception handling
import threading               # Thread management

from poly_data.polymarket_client import PolymarketClient
from poly_data.data_utils import update_markets, update_positions, update_orders
from poly_data.websocket_handlers import connect_market_websocket, connect_user_websocket
import poly_data.global_state as global_state
from poly_data.data_processing import remove_from_performing
from dotenv import load_dotenv

load_dotenv()

def update_once():
    """
    Initialize the application state by fetching market data, positions, and orders.
    """
    update_markets()    # Get market information from Google Sheets
    update_positions()  # Get current positions from Polymarket
    update_orders()     # Get current orders from Polymarket

def remove_from_pending():
    """
    Clean up stale trades that have been pending for too long (>15 seconds).
    This prevents the system from getting stuck on trades that may have failed.
    """
    try:
        current_time = time.time()

        # Iterate through all performing trades
        # Keep lock held throughout to prevent race conditions
        with global_state.lock:
            items = [(col, list(ids)) for col, ids in global_state.performing.items()]

            for col, trade_ids in items:
                for trade_id in trade_ids:
                    try:
                        # If trade has been pending for more than 15 seconds, remove it
                        if col not in global_state.performing_timestamps:
                            continue

                        timestamp = global_state.performing_timestamps[col].get(trade_id, current_time)

                        if current_time - timestamp > 15:
                            print(f"Removing stale entry {trade_id} from {col} after 15 seconds")
                            # Remove directly instead of calling remove_from_performing to avoid nested lock
                            if col in global_state.performing:
                                global_state.performing[col].discard(trade_id)

                            if col in global_state.performing_timestamps:
                                global_state.performing_timestamps[col].pop(trade_id, None)

                            print("After removing: ", global_state.performing, global_state.performing_timestamps)
                    except Exception as e:
                        print(f"Error removing specific trade {trade_id}: {e}")
                        print(traceback.format_exc())
    except Exception as e:
        print(f"Error in remove_from_pending: {e}")
        print(traceback.format_exc())

def update_periodically():
    """
    Background thread function that periodically updates market data, positions and orders.
    - Positions and orders are updated every 5 seconds
    - Market data is updated every 30 seconds (every 6 cycles)
    - Stale pending trades are removed each cycle
    - Garbage collection runs every 60 seconds to reduce overhead
    """
    i = 1
    while True:
        time.sleep(5)  # Update every 5 seconds

        try:
            # Clean up stale trades
            remove_from_pending()

            # Update positions and orders every cycle
            update_positions(avgOnly=True)  # Only update average price, not position size
            update_orders()

            # Update market data every 6th cycle (30 seconds)
            if i % 6 == 0:
                update_markets()

            # Run garbage collection every 60 seconds (every 12th cycle) to reduce overhead
            if i % 12 == 0:
                gc.collect()
                i = 1

            i += 1
        except Exception as e:
            print(f"Error in update_periodically: {e}")
            print(traceback.format_exc())
            
async def main():
    """
    Main application entry point. Initializes client, data, and manages websocket connections.
    """
    # Initialize client
    global_state.client = PolymarketClient()
    
    # Initialize state and fetch initial data
    global_state.all_tokens = []
    update_once()
    print("After initial updates: ", global_state.orders, global_state.positions)

    print("\n")
    print(f'There are {len(global_state.df)} market, {len(global_state.positions)} positions and {len(global_state.orders)} orders. Starting positions: {global_state.positions}')

    # Start background update thread
    update_thread = threading.Thread(target=update_periodically, daemon=True)
    update_thread.start()
    
    # Main loop - maintain websocket connections
    while True:
        try:
            # Connect to market and user websockets simultaneously
            await asyncio.gather(
                connect_market_websocket(global_state.all_tokens), 
                connect_user_websocket()
            )
            print("Reconnecting to the websocket")
        except Exception as e:
            print(f"Error in main loop: {e}")
            print(traceback.format_exc())

        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
