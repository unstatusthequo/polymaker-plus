import asyncio                      # Asynchronous I/O
import json                        # JSON handling
import websockets                  # WebSocket client
import traceback                   # Exception handling

from poly_data.data_processing import process_data, process_user_data
import poly_data.global_state as global_state

async def connect_market_websocket(chunk):
    """Connect to the market WebSocket with retry backoff and defensive parsing."""

    uri = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
    backoff = 1

    while True:
        if not chunk:
            print("No market tokens configured; waiting before subscribing")
            await asyncio.sleep(5)
            continue

        try:
            async with websockets.connect(uri, ping_interval=5, ping_timeout=None) as websocket:
                # Prepare and send subscription message
                message = {"assets_ids": chunk}
                await websocket.send(json.dumps(message))

                print("\n")
                print(f"Sent market subscription message: {message}")
                backoff = 1  # Reset backoff after a successful connection

                try:
                    # Process incoming market data indefinitely
                    while True:
                        message = await websocket.recv()
                        try:
                            json_data = json.loads(message)
                        except json.JSONDecodeError:
                            print(f"Failed to decode market message: {message}")
                            continue

                        # Process order book updates and trigger trading as needed
                        process_data(json_data)
                except websockets.ConnectionClosed:
                    print("Connection closed in market websocket")
                    print(traceback.format_exc())
                except Exception as e:
                    print(f"Exception in market websocket: {e}")
                    print(traceback.format_exc())
        except Exception as e:
            print(f"Failed to establish market websocket connection: {e}")
            print(traceback.format_exc())

        # Brief delay before attempting to reconnect, with capped exponential backoff
        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, 30)

async def connect_user_websocket():
    """Connect to the user WebSocket with retry backoff and safer message parsing."""

    uri = "wss://ws-subscriptions-clob.polymarket.com/ws/user"
    backoff = 1

    while True:
        try:
            async with websockets.connect(uri, ping_interval=5, ping_timeout=None) as websocket:
                # Prepare authentication message with API credentials
                message = {
                    "type": "user",
                    "auth": {
                        "apiKey": global_state.client.client.creds.api_key,
                        "secret": global_state.client.client.creds.api_secret,
                        "passphrase": global_state.client.client.creds.api_passphrase
                    }
                }

                # Send authentication message
                await websocket.send(json.dumps(message))

                print("\n")
                print(f"Sent user subscription message")
                backoff = 1  # Reset backoff after a successful connection

                try:
                    # Process incoming user data indefinitely
                    while True:
                        message = await websocket.recv()
                        try:
                            json_data = json.loads(message)
                        except json.JSONDecodeError:
                            print(f"Failed to decode user message: {message}")
                            continue

                        # Process trade and order updates
                        process_user_data(json_data)
                except websockets.ConnectionClosed:
                    print("Connection closed in user websocket")
                    print(traceback.format_exc())
                except Exception as e:
                    print(f"Exception in user websocket: {e}")
                    print(traceback.format_exc())
        except Exception as e:
            print(f"Failed to establish user websocket connection: {e}")
            print(traceback.format_exc())

        # Brief delay before attempting to reconnect, with capped exponential backoff
        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, 30)
