import base64
import io
import os.path
import sys
import time

import matplotlib
from PIL import Image
from PyQt5.QtWebEngineWidgets import QWebEngineView

matplotlib.use('Agg')
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QLabel, QTableView, \
    QStyledItemDelegate, QSizePolicy, QComboBox, QTextEdit, QMessageBox, QApplication, QFileDialog

from PyQt5.QtCore import Qt, QAbstractTableModel
from PyQt5.QtGui import QColor, QPixmap, QStandardItemModel, QStandardItem, QIcon
from app import *
from PyQt5.Qt import QTabWidget, QFont


class StartPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('CO2 Emissions finder')
        self.resize(450, 450)
        self.setMaximumSize(450, 450)
        self.icon = QLabel(self)

        p = QPixmap('icon.webp')
        self.icon.setPixmap(p)
        self.icon.setGeometry(0, 0, 450, 450)
        self.icon.setScaledContents(True)

        self.title = QLabel("CO2 Emissions finder", self)
        title_font = QFont('Arial', 12, QFont.Bold)
        self.title.setFont(title_font)
        self.title.setMinimumWidth(450)
        self.title.setGeometry(30, 20, 300, 61)
        font = self.title.font()
        font.setPointSize(20)
        self.title.setFont(font)

        self.text = QLabel("Software for visualisation&calculation \nof vehicle CO2 emissions data", self)
        text_font_ = QFont('Arial', 13, QFont.Bold)
        self.text.setFont(text_font_)
        text_font = QFont('Arial', 10, QFont.Normal)
        self.text.setStyleSheet("color: lightgreen;")
        self.text.setFont(text_font_)
        self.text.setGeometry(40, 300, 450, 61)
        # self.text.setScaledContents(True)
        self.title.setMinimumWidth(450)

        self.start_button = QPushButton("Getting Start", self)
        self.start_button.setFont(text_font)
        self.start_button.setGeometry(30, 380, 131, 51)
        self.start_button.clicked.connect(self.start_application)

        self.upload_button = QPushButton("Upload file", self)
        self.upload_button.setFont(text_font)
        self.upload_button.setGeometry(300, 380, 131, 51)
        self.upload_button.clicked.connect(self.start_upload)

    def start_application(self):
        self.main_window = RoutePlannerApp()
        self.main_window.show()
        self.hide()

    def start_upload(self):
        self.upload_window = UpLoadPage()
        self.upload_window.show()
        self.hide()


class PandasModel(QAbstractTableModel):
    def __init__(self, data):
        super(PandasModel, self).__init__()
        self._data = data

    def rowCount(self, parent=None):
        return self._data.shape[0]

    def columnCount(self, parent=None):
        return self._data.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and index.isValid():
            return str(self._data.iloc[index.row(), index.column()])
        return None

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._data.columns[section]
        return None


class ColorDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        if index.column() == 1:  # Color column
            painter.fillRect(option.rect, QColor(index.data()))
            painter.drawText(option.rect.adjusted(5, 0, 0, 0), Qt.AlignCenter,
                             index.model().data(index.model().index(index.row(), 0)))


class RoutePlannerApp(QWidget):
    # def __init__(self, api_key, plot_routes, plot_eco_route_callback, collect_distances_callback,get_emissions_chart_path):
    def __init__(self):
        super().__init__()
        self.car_data = read_csv()
        self.brand_tag, self.class_tag, self.fuel_tag = parser_data(self.car_data)

        self.tabw = QTabWidget()
        self.initUI()
        self.init_cal_ui()

    def initUI(self):

        self.tab1 = QWidget()
        self.tab1.setLayout(QVBoxLayout())
        self.tabw.addTab(self.tab1, "Route Planner")

        self.setWindowTitle('CO2 Emissions finder')
        self.resize(1600, 900)

        main_layout = QVBoxLayout(self)

        # Input bar and Draw Route Button
        input_layout = QHBoxLayout()
        self.start_input = QLineEdit()
        self.end_input = QLineEdit()
        input_layout.addWidget(QLabel('Departure:'))
        input_layout.addWidget(self.start_input)
        input_layout.addWidget(QLabel('Destination:'))
        input_layout.addWidget(self.end_input)
        plot_button = QPushButton('Plot Routes', self)
        plot_button.clicked.connect(self.plot_and_collect_distances)
        input_layout.addWidget(plot_button)
        self.tab1.layout().addLayout(input_layout)

        # layout of plot routes
        self.map_layout = QHBoxLayout()
        self.map_view_standard = QWebEngineView()
        self.map_view_standard.setMinimumSize(600, 400)
        self.map_view_eco = QWebEngineView()
        self.map_view_eco.setMinimumSize(600, 400)
        self.map_layout.addWidget(self.map_view_standard)
        self.map_layout.addWidget(self.map_view_eco)
        self.tab1.layout().addLayout(self.map_layout)

        # The left vertical layout includes a pattern color table and a data table
        left_layout = QVBoxLayout()
        self.mode_color_table = QTableView()
        data = {
            'Mode': ['Car', 'Train', 'DIESEL', 'GASOLINE', 'Electric', 'HYBRID'],
            'Color': ['#0000FF', '#FF0000', '#006400', '#FFA500', '#FFFF00', '#90EE90']
        }
        df = pd.DataFrame(data)
        self.mode_color_table.setModel(PandasModel(df))
        self.mode_color_table.setItemDelegate(ColorDelegate())
        left_layout.addWidget(self.mode_color_table)
        self.table_view = QTableView()
        self.table_view.setMinimumWidth(550)
        self.table_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        left_layout.addWidget(self.table_view)

        # Add drawing canvas on the right side
        self.emissions_chart_label = QLabel(self)
        self.emissions_chart_label.setMinimumSize(800, 450)
        self.emissions_chart_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Organize left and right layouts
        data_chart_layout = QHBoxLayout()
        data_chart_layout.addLayout(left_layout)
        data_chart_layout.addWidget(self.emissions_chart_label)

        self.tab1.layout().addLayout(data_chart_layout)

        main_layout.addWidget(self.tabw)

        self.back_main_btn = QPushButton()
        self.back_main_btn.setMaximumSize(100, 30)
        self.back_main_btn.setText('<-Back')
        self.back_main_btn.clicked.connect(self.back_main)
        data_chart_layout.addWidget(self.back_main_btn,alignment=Qt.AlignRight|Qt.AlignBottom)

    def init_cal_ui(self):
        self.car_brand_combo_box = QComboBox()
        # self.car_brand_combo_box.setFixedWidth(250)
        self.car_class_combo_box = QComboBox()
        # self.car_class_combo_box.setFixedWidth(250)
        self.car_fuel_combo_box = QComboBox()
        # self.car_fuel_combo_box.setFixedWidth(250)
        tab = QWidget()

        tab.setLayout(QVBoxLayout())
        for brand in self.brand_tag:
            self.car_brand_combo_box.addItem(brand)

        self.car_brand_combo_box.currentIndexChanged.connect(self.update_class)
        self.car_class_combo_box.currentIndexChanged.connect(self.update_fuel)

        select_layout = QHBoxLayout()

        select_layout.addWidget(QLabel("Brand:"))
        select_layout.addWidget(self.car_brand_combo_box, 4, Qt.AlignLeft)
        select_layout.addWidget(QLabel("Class:"))
        select_layout.addWidget(self.car_class_combo_box, 4, Qt.AlignLeft)
        select_layout.addWidget(QLabel("Fuel:"))
        select_layout.addWidget(self.car_fuel_combo_box, 4, Qt.AlignLeft)

        search_button = QPushButton()
        search_button.setText("Search")
        search_button.clicked.connect(self.search_car)

        select_layout.addWidget(search_button)

        cal_layout = QHBoxLayout()
        cal_layout.addWidget(QLabel("Distance(km):"))
        self.distance_line_edit = QLineEdit()
        cal_layout.addWidget(self.distance_line_edit, 4, Qt.AlignLeft)

        cal_button = QPushButton()
        cal_button.setText("Calculate")
        cal_button.clicked.connect(self.calculate_carbon)
        cal_layout.addWidget(cal_button)

        tab.layout().addLayout(select_layout)
        tab.layout().addLayout(cal_layout)

        self.model = QStandardItemModel()
        self.column_name = ['Car Name', 'Car Class', 'Car Fuel', 'OfficialCO2', 'select']

        self.table_view2 = QTableView()
        self.table_view2.setMinimumWidth(750)
        self.table_view2.setModel(self.model)
        header = self.table_view2.horizontalHeader()
        # header.setSectionResizeMode(QHeaderView.Interactive)
        # header.resizeSection(0, 100)
        # header.resizeSection(1, 350)
        # header.resizeSection(2, 100)
        # header.resizeSection(3, 100)
        # header.resizeSection(4, 100)
        self.model.setHorizontalHeaderLabels(self.column_name)

        result_layout = QHBoxLayout()
        result_layout.addWidget(self.table_view2)

        self.result_text_edit = QTextEdit()
        result_layout.addWidget(self.result_text_edit)

        tab.layout().addLayout(result_layout)

        self.tabw.addTab(tab, "Calculator")

        self.setGeometry(300, 300, 300, 200)
        self.show()

    def plot_and_collect_distances(self):
        start = self.start_input.text()
        end = self.end_input.text()
        try:
            distances_df, car_distance, train_distance = collect_distances_callback(API_KEY, start, end)
            self.distances_df = distances_df
            self.table_view.setModel(PandasModel(distances_df))

            self.emissions_data = calculate_emissions(car_distance, train_distance)

            plot_routes(API_KEY, start, end, self.map_view_standard)
            plot_eco_routes(API_KEY, start, end, self.map_view_eco)
            self.update_emissions_chart()

            self.table_view.resizeColumnsToContents()
            self.table_view.resizeRowsToContents()
        except Exception as e:
            self.show_dialog(str(e))

    def update_emissions_chart(self):
        image_path = get_emissions_chart_path(self.emissions_data)
        pixmap = QPixmap(image_path)
        self.emissions_chart_label.setPixmap(pixmap.scaled(self.emissions_chart_label.size(), Qt.IgnoreAspectRatio))

    def search_car(self):
        self.model = QStandardItemModel()
        self.column_name = ['Car Name', 'Car Class', 'Car Fuel', 'OfficialCO2', 'select']
        self.model.setHorizontalHeaderLabels(self.column_name)
        data_list = search_data(self.car_data, self.car_brand_combo_box.currentText(),
                                self.car_class_combo_box.currentText(), self.car_fuel_combo_box.currentText())
        # self.model.setHorizontalHeaderLabels(['Car Name', 'Car Class', 'Car Fuel','select','Result'])
        for data in data_list:
            car_name_item = QStandardItem(str(data['Car_name']))
            car_class_item = QStandardItem(str(data['ModelName']))
            car_fuel_item = QStandardItem(str(data['FuelType']))
            car_co2_item = QStandardItem(str(data['OfficialCO2']))
            select_item = QStandardItem()  # use for checkbox column
            select_item.setCheckable(True)
            self.model.appendRow([car_name_item, car_class_item, car_fuel_item, car_co2_item, select_item])
        self.table_view2.setModel(self.model)
        self.table_view2.resizeColumnsToContents()
        self.table_view2.resizeRowsToContents()

    def calculate_carbon(self):
        text = ''
        for row in range(self.model.rowCount()):
            try:
                car_name = self.model.item(row, 0).text()
                check_item = self.model.item(row, 4)  # The fourth column is the checkbox column
                data = float(self.model.item(row, 3).text())
                distance = float(self.distance_line_edit.text())
                if check_item is not None and check_item.checkState() == Qt.Checked:
                    text += car_name.strip() + '\n' + 'CO2emissions:' + str(data * distance) + '\n'

            except Exception as e:
                print(e)
        self.result_text_edit.setText(text)

    def update_class(self):
        self.car_class_combo_box.clear()
        class_set = set()
        car_brand = self.car_brand_combo_box.currentText()
        for i in self.car_data:
            if i['ManufacturerName'] == car_brand:
                class_set.add(i['ModelName'])

        for j in class_set:
            self.car_class_combo_box.addItem(j)

    def update_fuel(self):
        self.car_fuel_combo_box.clear()
        fuel_set = set()
        car_brand = self.car_brand_combo_box.currentText()
        car_class = self.car_class_combo_box.currentText()
        for i in self.car_data:
            if i['ManufacturerName'] == car_brand:
                if i['ModelName'] == car_class:
                    fuel_set.add(i['FuelType'])

        for j in fuel_set:
            self.car_fuel_combo_box.addItem(j)

    def show_dialog(self, message):
        QMessageBox.critical(self, "Error", f"Please input location!")

    def back_main(self):
        self.main_window = StartPage()
        self.main_window.show()
        self.close()


class UpLoadPage(QWidget):
    def __init__(self):
        super(UpLoadPage, self).__init__()
        self.setAcceptDrops(True)
        self.setWindowTitle('CO2 Emissions finder')
        self.setMaximumSize(280, 360)
        self.setMinimumHeight(340)

        self.label_1 = QLabel(self)
        self.label_1.setGeometry(5, 0, 270, 270)
        self.label_1.setText('Drag a Excel file to here!')
        self.label_1.setAlignment(Qt.AlignCenter)
        self.label_1.setStyleSheet("border: 2px dashed gray;")

        self.upload_btn = QPushButton(self)
        self.upload_btn.setText('Upload')
        self.upload_btn.clicked.connect(self.upload)
        self.upload_btn.setGeometry(10, 280, 130, 50)

        self.generate_btn = QPushButton(self)
        self.generate_btn.setText('Generate')
        self.generate_btn.clicked.connect(self.save_file)
        # self.setAcceptDrops(True)

        self.generate_btn.setGeometry(140, 280, 130, 50)

        self.back_main_btn = QPushButton(self)
        # self.back_main_btn = QPushButton()
        self.back_main_btn.setMaximumSize(100, 30)
        self.back_main_btn.setGeometry(7, 1, 100, 30)
        self.back_main_btn.setText('<-Back')
        self.back_main_btn.clicked.connect(self.back_main)

        self.offset_combox = QComboBox(self)
        self.offset_combox.setGeometry(160, 1, 110, 30)
        self.offset_combox.addItems(['0%', '+5%/-5%', '+10%/-10%'])
        # .addWidget(self.back_main_btn, alignment=Qt.AlignRight | Qt.AlignBottom)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            self.file_path = url.toLocalFile()
            file_path = self.file_path.split('/')[-1]
            self.label_1.setText(file_path)

    def upload(self):
        excel_file, _ = QFileDialog.getOpenFileName(self, 'Open file', 'C:\\', 'All Files(*)')
        self.file_path = excel_file
        self.label_1.setText(self.file_path.split('/')[-1])
        if not self.file_path:
            self.label_1.setText('Drag a Excel file to here!')

    def save_file(self):
        offset =  self.offset_combox.currentText()
        if offset == '0%':
            offset = 0
        elif offset == '+5%/-5%':
            offset = 0.5
        else:
            offset = 0.1
        df, flag = analyse_file(self.file_path, offset)
        if not flag:
            return
        # df[['Distance (km)', 'CO2 Emissions (g)']] = df.apply(df_series, axis=1)
        excel_file, _ = QFileDialog.getSaveFileName(self, 'Save file', 'C:\\', 'xlsx(*.xlsx)')
        if excel_file:
            df.to_excel(excel_file, index=False)
            if os.path.exists(excel_file):
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Information)
                msg.setText("File Saved！")
                msg.setWindowTitle("Save")
                msg.exec_()

    def back_main(self):
        self.main_window = StartPage()
        self.main_window.show()
        self.close()


"""" 
        car_distance = distances_df.loc[0, 'distance']  # 假设第一行是汽车距离
        train_distance = distances_df.loc[1, 'distance']  # 假设第二行是火车距离
        emissions_data = self.calculate_emissions(car_distance, train_distance)
        self.plot_emission_chart(emissions_data)

        car_distance = float(distances_df.loc[distances_df['Mode'] == 'car', 'Distance'].values[0])
        train_distance = float(distances_df.loc[distances_df['Mode'] == 'train', 'Distance'].values[0])
"""""

"""
    def plot_emission_chart(self, emissions_data):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        modes = list(emissions_data.keys())
        emissions = list(emissions_data.values())
        ax.bar(modes, emissions, color='orange')
        ax.set_title('CO2 Emissions by Transport Mode')
        ax.set_ylabel('Emissions (g)')
        self.canvas.draw()
"""

if __name__ == "__main__":
    # API_KEY = 'AIzaSyD4uF8UsInRixMuU_sRK402WrLbBRYlZiY'
    app = QApplication(sys.argv)
    ex = StartPage()
    ex.show()
    sys.exit(app.exec_())
    # app = QApplication(sys.argv)
