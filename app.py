import folium
import requests
import tempfile
from PyQt5.QtCore import QUrl
import pandas as pd
import matplotlib.pyplot as plt
from pprint import pprint
import googlemaps
from PyQt5.QtWidgets import QMessageBox

API_KEY = 'AIzaSyD4uF8UsInRixMuU_sRK402WrLbBRYlZiY'


def get_directions(api_key, start, end, mode='driving', emission_type=None):
    base_url = "https://maps.googleapis.com/maps/api/directions/json?"
    params = f"origin={start}&destination={end}&mode={mode}&key={api_key}"
    if emission_type:
        params += f"&vehicle_emission_type={emission_type}"
    response = requests.get(f"{base_url}{params}")
    if response.status_code == 200:
        return response.json()
    else:
        return None


def plot_routes(api_key, start, end, map_view_standard):
    map_obj_standard = folium.Map(location=[54.5, -3.0], zoom_start=5.5)
    modes = [('driving', 'blue'), ('transit', 'red')]
    for mode, color in modes:
        directions = get_directions(api_key, start, end, mode=mode)
        if directions and directions['routes']:
            for route in directions['routes']:
                folium.PolyLine(
                    locations=[(step['end_location']['lat'], step['end_location']['lng'])
                               for leg in route['legs'] for step in leg['steps']],
                    weight=5,
                    color=color
                ).add_to(map_obj_standard)

        with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as tmpfile:
            map_obj_standard.save(tmpfile.name)
            file_url = QUrl.fromLocalFile(tmpfile.name)
            # print(f"Map is saved to: {tmpfile.name}")  # 打印文件路径
            # print(f"Map URL is: {file_url.toString()}")  # 打印 URL
            map_view_standard.load(file_url)

        #   map_view_standard.loadFinished.connect(on_load_finished)  # 连接信号到槽


"""
def on_load_finished(success):
    if success:
            print("Map loaded successfully in QWebEngineView.")
    else:
            print("Failed to load the map in QWebEngineView.")

"""
"""""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as tmpfile:
             map_obj_standard.save(tmpfile.name)
             map_view_standard.load(QUrl.fromLocalFile(tmpfile.name))
             # print(tmpfile.name)
             return True
"""""


def offset_coordinates(lat, lon, offset=1000):
    # Shift function, shifting north and east
    return (lat + offset, lon + offset)


def plot_eco_routes(api_key, start, end, map_view_eco):
    map_obj_eco = folium.Map(location=[54.5, -3.0], zoom_start=5.5)
    emission_types = [
        ('DIESEL', 'darkgreen', 0.01),  # color, offset
        ('GASOLINE', 'orange', 0.008),
        ('ELECTRIC', 'yellow', 0.006),
        ('HYBRID', 'lightgreen', 0.004)
    ]

    for emission_type, color, offset in emission_types:
        directions = get_directions(api_key, start, end, mode='driving', emission_type=emission_type)
        if directions and directions['routes']:
            for route in directions['routes']:
                original_polyline = [
                    (step['end_location']['lat'], step['end_location']['lng'])
                    for leg in route['legs'] for step in leg['steps']
                ]
                offset_polyline = [offset_coordinates(lat, lon, offset) for lat, lon in original_polyline]
                folium.PolyLine(offset_polyline, weight=4, color=color, opacity=0.8).add_to(map_obj_eco)
            print(f"Route plotted for {emission_type}: {color}")
        else:
            print(f"No route data returned for {emission_type}, or error in data.")

    with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as tmpfile:
        map_obj_eco.save(tmpfile.name)
        map_view_eco.load(QUrl.fromLocalFile(tmpfile.name))
        # print(f"Eco map saved to {tmpfile.name}")
        return True


def collect_distances_callback(api_key, start, end):
    modes = [('car', 'driving'), ('train', 'transit')]
    emission_types = ['DIESEL', 'GASOLINE', 'ELECTRIC', 'HYBRID']

    # Initialize an empty dictionary to collect distance data
    distance_data = {'distance': []}

    # Collect distance data for cars and trains
    for label, mode in modes:
        directions = get_directions(api_key, start, end, mode=mode)
        if directions and 'routes' in directions and directions['routes']:
            distance_data['distance'].append(f"{label}: {directions['routes'][0]['legs'][0]['distance']['text']}")
        else:
            distance_data['distance'].append(f"{label}: No data")

    # Collect distance data for environmentally friendly vehicles
    eco_distances = []
    for emission_type in emission_types:
        directions = get_directions(api_key, start, end, mode='driving', emission_type=emission_type)
        if directions and 'routes' in directions and directions['routes']:
            eco_distances.append(f"{emission_type}: {directions['routes'][0]['legs'][0]['distance']['text']}")
        else:
            eco_distances.append(f"{emission_type}: No data")
    # Merge the distance of environmentally friendly vehicles into one record
    distance_data['distance'].append("eco-friendly: " + ", ".join(eco_distances))

    # create DataFrame
    # distances_df = pd.DataFrame(distance_data)
    #
    # return distances_df

    import re
    try:
        car_distance = re.findall('\d+', distance_data['distance'][0])[0]
        train_distance = re.findall('\d+', distance_data['distance'][1])[0]
    except:
        car_distance = None
        train_distance = None

    distances_df = pd.DataFrame(distance_data)
    return distances_df, car_distance, train_distance


def calculate_emissions(car_distance, train_distance):
    emission_factors = {
        'Diesel': 164.0,
        'Gasoline': 143.0,
        'Hybrid': 126.2,
        'Plug-in Hybrid': 35.1,
        'BEVs': 0.0,
        'FCEVs': 0.0,
        'Train': 33.0
    }

    emissions = {}
    for mode, factor in emission_factors.items():
        distance = car_distance if mode != 'Train' else train_distance
        if distance is not None:
            emissions[mode] = float(distance) * factor

    emissions_df = pd.DataFrame(list(emissions.items()), columns=['Mode', 'Emissions'])
    return emissions_df


def get_emissions_chart_path(emissions_df):
    # create a barchart
    fig, ax = plt.subplots()
    bars = emissions_df.set_index('Mode')['Emissions'].plot(kind='bar', ax=ax, color='orange')
    ax.set_title('CO2 Emissions by Transport Mode')
    ax.set_ylabel('Emissions (g/km)')
    ax.set_xlabel('Transport Mode')
    ax.set_xticklabels(ax.get_xticklabels(), rotation=0, fontsize=9)

    # Add values to each bar
    for bar in bars.patches:
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                f'{bar.get_height():.2f}', ha='center', va='bottom', fontsize=9, color='black')

    # save as temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    plt.savefig(temp_file.name)
    plt.close()

    print(f"Chart saved to: {temp_file.name}")  # print path to test tmpfile successfully generated
    return temp_file.name


def read_csv():
    car_data = pd.read_csv('car_data.csv').to_dict(orient='records')
    return car_data


def parser_data(car_data):
    car_brand_list = {''}
    car_class_list = {''}
    fuel_type_list = {''}
    for data in car_data:
        car_brand_list.add(data['ManufacturerName'])
        car_class_list.add(data['ModelName'])
        fuel_type_list.add(data['FuelType'])

    return car_brand_list, car_class_list, fuel_type_list


def search_data(car_data, brand=None, class_=None, fuel=None):
    output_list = []
    for data in car_data:
        if brand:
            if brand != data['ManufacturerName']:
                continue
        if class_:
            if class_ != data['ModelName']:
                continue
        if fuel:
            if fuel != data['FuelType']:
                continue
        output_list.append(data)
    return output_list

def analyse_file(file_path,offset_):
  try:
    # Load the Excel file
    df = pd.read_excel(file_path)

    # Initialize Google Maps
    gmaps = googlemaps.Client(key='AIzaSyD4uF8UsInRixMuU_sRK402WrLbBRYlZiY')

    # Emission factors in grams per kilometer
    emission_factors = {
        'Diesel': 164.0,
        'Gasoline': 143.0,
        'Hybrid': 126.2,
        'Plug-in Hybrid': 35.1,
        'BEVs': 0.0,
        'FCEVs': 0.0,
        'Train': 33.0
    }

    # Function to fetch distance and calculate emissions
    def calculate_emissions(row):
        # Determine the mode based on transport type
        if row['Transport Mode'] == 'Train':
            mode = 'transit'
        else:
            mode = 'driving'

        # Call Google Maps Distance Matrix API
        result = gmaps.distance_matrix(origins=row['Departure'], destinations=row['Destination'], mode=mode)

        # Check if the API call was successful
        if result['rows'][0]['elements'][0]['status'] == 'OK':
            distance = result['rows'][0]['elements'][0]['distance']['value'] / 1000  # Convert meters to kilometers
            emissions = distance * emission_factors[row['Transport Mode']]
        else:
            distance, emissions = 0, 0  # Handle errors or no results by setting zero values

        return pd.Series([distance, emissions])

    def highlight_cols(s):

        # Obtain the distance from the document and the actual distance
        col1 = s.iloc[-2]
        col2 = s.iloc[-3]
        # Creates a list of styles with the same number of columns, initially as an empty string
        colors = [''] * len(s)
        # Compares distance and actual distance
        if float(col1) > float(col2)*(1+offset_):
            colors[-2] = 'background-color: red'
            # colors[-3] = 'background-color: green'
        elif float(col1) < float(col2)*(1-offset_):
            colors[-2] = 'background-color: green'
            # colors[-3] = 'background-color: red'
        # return colored list by the acceptable range
        return colors

    # Apply the function to each row in DataFrame
    # df[['Distance (km)', 'CO2 Emissions (g)']] = df.apply(calculate_emissions, axis=1)
    df[['exact distance', 'CO2 Emissions (g)']] = df.apply(calculate_emissions, axis=1)

    styled_df = df.style.apply(highlight_cols, axis=1)

    show_success_message()
    return styled_df, True
  except Exception as e:
    show_error_message(str(e))  # Call to show the error message
    return None, False
    # Optional: return None or handle differently based on your application's needs

def show_error_message(error):
      # This function creates and displays an error message box
      msg = QMessageBox()
      msg.setIcon(QMessageBox.Critical)
      msg.setText("Generates failed!")
      msg.setInformativeText(f"Error details: {error}")
      msg.setWindowTitle("Error")
      msg.setStandardButtons(QMessageBox.Ok)
      msg.exec_()
    # Save the updated DataFrame to a new Excel file
    # df.to_excel('Updated_UK_Transport_Data.xlsx', index=False)

def show_success_message():
    # This function creates and displays an error message box
    msg = QMessageBox()
    # msg.setIcon(QMessageBox.)
    msg.setText("Generates success!")
    # msg.setInformativeText(f"Error details: {error}")
    msg.setWindowTitle("Success")
    msg.setStandardButtons(QMessageBox.Ok)
    msg.exec_()


if __name__ == "__main__":
    pprint(read_csv())
