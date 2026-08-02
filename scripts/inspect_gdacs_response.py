import httpx

GDACS_URL = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/EVENTS4APP"

print("Connecting...")

try:
    with httpx.Client(
        timeout=httpx.Timeout(
            connect=20.0,
            read=120.0,
            write=20.0,
            pool=20.0
        ),
        follow_redirects=True
    ) as client:

        response = client.get(GDACS_URL)

        print("Status Code:", response.status_code)

        print()

        print("Headers:")

        print(response.headers)

        print()

        print("First 1000 characters:")

        print(response.text[:1000])

except Exception as e:

    print(type(e).__name__)

    print(e)