import boto3
import pandas as pd
import matplotlib.pyplot as plt

# ==============================
# AWS CONFIGURATION
# ==============================

REGION = "ap-southeast-2"
TABLE_NAME = "IoTSensorData"
PROFILE = "IoTAnalysisUser"

# ==============================
# CONNECT TO AWS
# ==============================

session = boto3.Session(
    profile_name=PROFILE,
    region_name=REGION
)

dynamodb = session.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)

print("========================================")
print("       AWS IoT SENSOR DATA ANALYSIS")
print("========================================")
print()

# ==============================
# READ DATA FROM DYNAMODB
# ==============================

response = table.scan()
items = response.get("Items", [])

while "LastEvaluatedKey" in response:
    response = table.scan(
        ExclusiveStartKey=response["LastEvaluatedKey"]
    )
    items.extend(response.get("Items", []))

print("Total records retrieved:", len(items))
print()

# ==============================
# CREATE DATAFRAME
# ==============================

data = []

for item in items:

    sensor_data = item.get("sensor_data", {})

    row = {
        "device_id": item.get("device_id"),
        "timestamp": float(item.get("timestamp", 0)),
        "temperature": float(sensor_data.get("temperature", 0)),
        "humidity": float(sensor_data.get("humidity", 0)),
        "pressure": float(sensor_data.get("pressure", 0))
    }

    data.append(row)

df = pd.DataFrame(data)

# ==============================
# SORT AND CONVERT TIME
# ==============================

df = df.sort_values("timestamp")

df["datetime"] = pd.to_datetime(
    df["timestamp"],
    unit="ms"
)

# ==============================
# STATISTICS
# ==============================

average_temperature = df["temperature"].mean()
minimum_temperature = df["temperature"].min()
maximum_temperature = df["temperature"].max()

average_humidity = df["humidity"].mean()
minimum_humidity = df["humidity"].min()
maximum_humidity = df["humidity"].max()

average_pressure = df["pressure"].mean()
minimum_pressure = df["pressure"].min()
maximum_pressure = df["pressure"].max()

# ==============================
# HIGH TEMPERATURE DETECTION
# ==============================

TEMPERATURE_THRESHOLD = 30.0

high_temperature = df[
    df["temperature"] > TEMPERATURE_THRESHOLD
]

high_temperature_count = len(high_temperature)

# ==============================
# DISPLAY RESULTS
# ==============================

print("========================================")
print("          SENSOR ANALYSIS RESULTS")
print("========================================")

print()

print("Device ID              :", df["device_id"].iloc[0])
print("Total Readings         :", len(df))

print()

print("------------- TEMPERATURE --------------")

print("Average Temperature    :",
      round(average_temperature, 2), "°C")

print("Minimum Temperature    :",
      round(minimum_temperature, 2), "°C")

print("Maximum Temperature    :",
      round(maximum_temperature, 2), "°C")

print()

print("--------------- HUMIDITY ----------------")

print("Average Humidity       :",
      round(average_humidity, 2), "%")

print("Minimum Humidity       :",
      round(minimum_humidity, 2), "%")

print("Maximum Humidity       :",
      round(maximum_humidity, 2), "%")

print()

print("---------------- PRESSURE ---------------")

print("Average Pressure       :",
      round(average_pressure, 2), "hPa")

print("Minimum Pressure       :",
      round(minimum_pressure, 2), "hPa")

print("Maximum Pressure       :",
      round(maximum_pressure, 2), "hPa")

print()

print("--------- HIGH TEMPERATURE --------------")

print("Threshold              :",
      TEMPERATURE_THRESHOLD, "°C")

print("High Temperature Count :",
      high_temperature_count)

if high_temperature_count > 0:
    print("Status                 : HIGH TEMPERATURE DETECTED")
else:
    print("Status                 : NORMAL")

print()

# ==============================
# EXPORT DATA TO CSV
# ==============================

df.to_csv(
    "sensor_data.csv",
    index=False
)

print("CSV file created: sensor_data.csv")

# ==============================
# CREATE ANALYSIS REPORT
# ==============================

with open("analysis_report.txt", "w") as file:

    file.write("========================================\n")
    file.write("       AWS IoT SENSOR ANALYSIS REPORT\n")
    file.write("========================================\n\n")

    file.write(
        "Device ID: "
        + str(df["device_id"].iloc[0])
        + "\n"
    )

    file.write(
        "Total Readings: "
        + str(len(df))
        + "\n\n"
    )

    file.write("------------- TEMPERATURE --------------\n")

    file.write(
        "Average Temperature: "
        + str(round(average_temperature, 2))
        + " °C\n"
    )

    file.write(
        "Minimum Temperature: "
        + str(round(minimum_temperature, 2))
        + " °C\n"
    )

    file.write(
        "Maximum Temperature: "
        + str(round(maximum_temperature, 2))
        + " °C\n\n"
    )

    file.write("--------------- HUMIDITY ----------------\n")

    file.write(
        "Average Humidity: "
        + str(round(average_humidity, 2))
        + " %\n"
    )

    file.write(
        "Minimum Humidity: "
        + str(round(minimum_humidity, 2))
        + " %\n"
    )

    file.write(
        "Maximum Humidity: "
        + str(round(maximum_humidity, 2))
        + " %\n\n"
    )

    file.write("---------------- PRESSURE ---------------\n")

    file.write(
        "Average Pressure: "
        + str(round(average_pressure, 2))
        + " hPa\n"
    )

    file.write(
        "Minimum Pressure: "
        + str(round(minimum_pressure, 2))
        + " hPa\n"
    )

    file.write(
        "Maximum Pressure: "
        + str(round(maximum_pressure, 2))
        + " hPa\n\n"
    )

    file.write("--------- HIGH TEMPERATURE --------------\n")

    file.write(
        "Threshold: "
        + str(TEMPERATURE_THRESHOLD)
        + " °C\n"
    )

    file.write(
        "High Temperature Count: "
        + str(high_temperature_count)
        + "\n"
    )

    if high_temperature_count > 0:
        file.write(
            "Status: HIGH TEMPERATURE DETECTED\n"
        )
    else:
        file.write(
            "Status: NORMAL\n"
        )

    file.write(
        "\n========================================\n"
    )

    file.write(
        "          ANALYSIS COMPLETED\n"
    )

    file.write(
        "========================================\n"
    )

print("Analysis report created: analysis_report.txt")

print()

# ==============================
# GRAPH 1 - TEMPERATURE
# ==============================

plt.figure(figsize=(12, 6))

plt.plot(
    df["datetime"],
    df["temperature"],
    marker="o",
    linewidth=1.5
)

plt.axhline(
    y=TEMPERATURE_THRESHOLD,
    linestyle="--",
    linewidth=2,
    label="High Temperature Threshold (30°C)"
)

plt.title("Temperature vs Time")
plt.xlabel("Time")
plt.ylabel("Temperature (°C)")
plt.xticks(rotation=45)
plt.grid(True)
plt.legend()
plt.tight_layout()

plt.savefig(
    "temperature_vs_time.png",
    dpi=300
)

plt.show()

# ==============================
# GRAPH 2 - HUMIDITY
# ==============================

plt.figure(figsize=(12, 6))

plt.plot(
    df["datetime"],
    df["humidity"],
    marker="o",
    linewidth=1.5
)

plt.title("Humidity vs Time")
plt.xlabel("Time")
plt.ylabel("Humidity (%)")
plt.xticks(rotation=45)
plt.grid(True)
plt.tight_layout()

plt.savefig(
    "humidity_vs_time.png",
    dpi=300
)

plt.show()

# ==============================
# GRAPH 3 - PRESSURE
# ==============================

plt.figure(figsize=(12, 6))

plt.plot(
    df["datetime"],
    df["pressure"],
    marker="o",
    linewidth=1.5
)

plt.title("Pressure vs Time")
plt.xlabel("Time")
plt.ylabel("Pressure (hPa)")
plt.xticks(rotation=45)
plt.grid(True)
plt.tight_layout()

plt.savefig(
    "pressure_vs_time.png",
    dpi=300
)

plt.show()

# ==============================
# COMPLETION
# ==============================

print("========================================")
print("       ANALYSIS COMPLETED")
print("========================================")

print()

print("Files created:")
print("1. sensor_data.csv")
print("2. analysis_report.txt")
print("3. temperature_vs_time.png")
print("4. humidity_vs_time.png")
print("5. pressure_vs_time.png")

print()
print("========================================")