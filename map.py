import folium
from folium import plugins
import tkinter as tk
from tkinter import ttk, messagebox, font
import sqlite3
from datetime import datetime
import webbrowser
import os
import requests
import json
import phonenumbers
from phonenumbers import geocoder, carrier, timezone
from geopy.geocoders import Nominatim
import threading

class PhoneLocationFinder:
    def __init__(self):
        # Khởi tạo thông tin người dùng và thời gian
        self.current_user = "TIENDEV"
        self.current_time = datetime.strptime("2025-06-06 03:42:22", "%Y-%m-%d %H:%M:%S")
        
        # API Keys
        self.google_maps_api_key = "AIzaSyA72HdZqkpHIAsy5iGPgzGzlXPscn8R2b8"
        
        # Khởi tạo các services
        self.geolocator = Nominatim(user_agent="phone_location_finder")
        self.session = requests.Session()
        
        # Cache cho kết quả tìm kiếm
        self.location_cache = {}
        
        # Khởi tạo các components
        self.init_database()
        self.init_region_data()
        self.create_gui()

    def init_database(self):
        """Khởi tạo và kết nối database"""
        self.conn = sqlite3.connect('phone_location_finder.db')
        self.cursor = self.conn.cursor()
        
        # Tạo bảng lưu lịch sử
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone_number TEXT,
                carrier TEXT,
                region TEXT,
                province TEXT,
                district TEXT,
                ward TEXT,
                street TEXT,
                full_address TEXT,
                latitude REAL,
                longitude REAL,
                accuracy REAL,
                timestamp DATETIME,
                user_id TEXT,
                search_method TEXT,
                result_data TEXT
            )
        ''')
        
        # Bảng cache
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS location_cache (
                phone_number TEXT PRIMARY KEY,
                carrier TEXT,
                location_data TEXT,
                timestamp DATETIME,
                expires_at DATETIME
            )
        ''')
        
        # Bảng thông tin cell towers
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS cell_towers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cell_id TEXT,
                carrier TEXT,
                latitude REAL,
                longitude REAL,
                region TEXT,
                coverage_radius REAL,
                last_updated DATETIME
            )
        ''')
        
        self.conn.commit()

    def init_region_data(self):
        """Khởi tạo dữ liệu vùng miền và tỉnh thành"""
        self.regions = {
            "Đồng bằng sông Hồng": {
                "center": {"lat": 20.8725, "lon": 105.9089},
                "provinces": [
                    {
                        "name": "Hà Nội",
                        "lat": 21.0285,
                        "lon": 105.8542,
                        "districts": [
                            "Ba Đình", "Hoàn Kiếm", "Hai Bà Trưng", "Đống Đa",
                            "Tây Hồ", "Cầu Giấy", "Thanh Xuân", "Hoàng Mai",
                            "Long Biên", "Nam Từ Liêm", "Bắc Từ Liêm", "Hà Đông"
                        ]
                    },
                    {"name": "Bắc Ninh", "lat": 21.1861, "lon": 106.0763},
                    {"name": "Hà Nam", "lat": 20.5835, "lon": 105.9229},
                    {"name": "Hải Dương", "lat": 20.9373, "lon": 106.3145},
                    {"name": "Hải Phòng", "lat": 20.8449, "lon": 106.6881},
                    {"name": "Hưng Yên", "lat": 20.6546, "lon": 106.0516},
                    {"name": "Nam Định", "lat": 20.4338, "lon": 106.1621},
                    {"name": "Thái Bình", "lat": 20.4464, "lon": 106.3366},
                    {"name": "Vĩnh Phúc", "lat": 21.3609, "lon": 105.5474}
                ]
            },
            "Đông Bắc Bộ": {
                "center": {"lat": 21.8725, "lon": 105.9089},
                "provinces": [
                    {"name": "Bắc Giang", "lat": 21.2771, "lon": 106.1947},
                    {"name": "Bắc Kạn", "lat": 22.1477, "lon": 105.8349},
                    {"name": "Cao Bằng", "lat": 22.6666, "lon": 106.2500},
                    {"name": "Hà Giang", "lat": 22.8237, "lon": 104.9834},
                    {"name": "Lạng Sơn", "lat": 21.8530, "lon": 106.7610},
                    {"name": "Phú Thọ", "lat": 21.3989, "lon": 105.1679},
                    {"name": "Quảng Ninh", "lat": 21.0063, "lon": 107.2925},
                    {"name": "Thái Nguyên", "lat": 21.5934, "lon": 105.8480},
                    {"name": "Tuyên Quang", "lat": 21.7767, "lon": 105.2280}
                ]
            },
            "Tây Bắc Bộ": {
                "center": {"lat": 21.3856, "lon": 103.0234},
                "provinces": [
                    {"name": "Điện Biên", "lat": 21.3856, "lon": 103.0234},
                    {"name": "Hòa Bình", "lat": 20.8132, "lon": 105.3379},
                    {"name": "Lai Châu", "lat": 22.3964, "lon": 103.4716},
                    {"name": "Lào Cai", "lat": 22.4856, "lon": 103.9733},
                    {"name": "Sơn La", "lat": 21.1024, "lon": 103.7289},
                    {"name": "Yên Bái", "lat": 21.7168, "lon": 104.9149}
                ]
            },
            "Bắc Trung Bộ": {
                "center": {"lat": 18.8256, "lon": 105.7852},
                "provinces": [
                    {"name": "Hà Tĩnh", "lat": 18.3556, "lon": 105.8877},
                    {"name": "Nghệ An", "lat": 19.2343, "lon": 104.9200},
                    {"name": "Quảng Bình", "lat": 17.4625, "lon": 106.6241},
                    {"name": "Quảng Trị", "lat": 16.7943, "lon": 107.0451},
                    {"name": "Thanh Hóa", "lat": 19.8067, "lon": 105.7762},
                    {"name": "Thừa Thiên Huế", "lat": 16.4637, "lon": 107.5909}
                ]
            },
            "Nam Trung Bộ": {
                "center": {"lat": 14.0583, "lon": 108.2772},
                "provinces": [
                    {"name": "Bình Định", "lat": 13.7829, "lon": 109.2196},
                    {"name": "Đà Nẵng", "lat": 16.0544, "lon": 108.2022},
                    {"name": "Khánh Hòa", "lat": 12.2388, "lon": 109.1967},
                    {"name": "Phú Yên", "lat": 13.0881, "lon": 109.0928},
                    {"name": "Quảng Nam", "lat": 15.5394, "lon": 108.0191},
                    {"name": "Quảng Ngãi", "lat": 15.1213, "lon": 108.7982}
                ]
            },
            "Tây Nguyên": {
                "center": {"lat": 12.6667, "lon": 108.0333},
                "provinces": [
                    {"name": "Đắk Lắk", "lat": 12.6667, "lon": 108.0333},
                    {"name": "Đắk Nông", "lat": 12.0040, "lon": 107.6874},
                    {"name": "Gia Lai", "lat": 13.9833, "lon": 108.0000},
                    {"name": "Kon Tum", "lat": 14.3544, "lon": 108.0003},
                    {"name": "Lâm Đồng", "lat": 11.9465, "lon": 108.4419}
                ]
            },
            "Đông Nam Bộ": {
                "center": {"lat": 10.8231, "lon": 106.6297},
                "provinces": [
                    {"name": "Bà Rịa-Vũng Tàu", "lat": 10.3466, "lon": 107.0843},
                    {"name": "Bình Dương", "lat": 11.1757, "lon": 106.6297},
                    {"name": "Bình Phước", "lat": 11.7511, "lon": 106.7235},
                    {"name": "Đồng Nai", "lat": 10.9574, "lon": 106.8426},
                    {"name": "TP. Hồ Chí Minh", "lat": 10.8231, "lon": 106.6297},
                    {"name": "Tây Ninh", "lat": 11.3009, "lon": 106.0986}
                ]
            },
            "Đồng bằng sông Cửu Long": {
                "center": {"lat": 10.0333, "lon": 105.7833},
                "provinces": [
                    {"name": "An Giang", "lat": 10.3864, "lon": 105.4380},
                    {"name": "Bạc Liêu", "lat": 9.2940, "lon": 105.7216},
                    {"name": "Bến Tre", "lat": 10.2433, "lon": 106.3752},
                    {"name": "Cà Mau", "lat": 9.1527, "lon": 105.1967},
                    {"name": "Cần Thơ", "lat": 10.0452, "lon": 105.7469},
                    {"name": "Đồng Tháp", "lat": 10.4938, "lon": 105.6882},
                    {"name": "Hậu Giang", "lat": 9.7579, "lon": 105.6413},
                    {"name": "Kiên Giang", "lat": 10.0215, "lon": 105.0965},
                    {"name": "Long An", "lat": 10.6069, "lon": 106.3240},
                    {"name": "Sóc Trăng", "lat": 9.6037, "lon": 105.9747},
                    {"name": "Tiền Giang", "lat": 10.3493, "lon": 106.3542},
                    {"name": "Trà Vinh", "lat": 9.9513, "lon": 106.3346},
                    {"name": "Vĩnh Long", "lat": 10.2540, "lon": 105.9722}
                ]
            }
        }
    
        # Thêm thông tin quận/huyện cho các tỉnh/thành phố lớn
        self.district_data = {
            "TP. Hồ Chí Minh": [
                "Quận 1", "Quận 3", "Quận 4", "Quận 5", "Quận 6", 
                "Quận 7", "Quận 8", "Quận 10", "Quận 11", "Quận 12",
                "Thủ Đức", "Gò Vấp", "Bình Thạnh", "Tân Bình", "Tân Phú",
                "Phú Nhuận", "Bình Tân", "Củ Chi", "Hóc Môn", "Bình Chánh",
                "Nhà Bè", "Cần Giờ"
            ],
            "Đà Nẵng": [
                "Hải Châu", "Thanh Khê", "Sơn Trà", "Ngũ Hành Sơn", 
                "Liên Chiểu", "Cẩm Lệ", "Hòa Vang"
            ],
            "Hải Phòng": [
                "Hồng Bàng", "Ngô Quyền", "Lê Chân", "Hải An",
                "Kiến An", "Đồ Sơn", "Dương Kinh"
            ],
            "Cần Thơ": [
                "Ninh Kiều", "Bình Thủy", "Cái Răng", "Ô Môn",
                "Thốt Nốt", "Phong Điền", "Cờ Đỏ", "Thới Lai", "Vĩnh Thạnh"
            ]
        }
        
        # Dữ liệu nhà mạng
        self.carriers = {
            "Viettel": {
                "prefixes": ['086', '096', '097', '098', '032', '033', '034', 
                            '035', '036', '037', '038', '039'],
                "mnc": "04",
                "coverage": "Toàn quốc",
                "headquarters": {"lat": 21.0259, "lon": 105.8550}
            },
            "Vinaphone": {
                "prefixes": ['088', '091', '094', '083', '084', '085', '081', '082'],
                "mnc": "02",
                "coverage": "Toàn quốc",
                "headquarters": {"lat": 21.0245, "lon": 105.8412}
            },
            "Mobifone": {
                "prefixes": ['089', '090', '093', '070', '079', '077', '076', '078'],
                "mnc": "01",
                "coverage": "Toàn quốc",
                "headquarters": {"lat": 21.0277, "lon": 105.8523}
            },
            "Vietnamobile": {
                "prefixes": ['092', '056', '058'],
                "mnc": "05",
                "coverage": "Đô thị lớn",
                "headquarters": {"lat": 10.7756, "lon": 106.7019}
            },
            "Gmobile": {
                "prefixes": ['099', '059'],
                "mnc": "07",
                "coverage": "Đô thị lớn",
                "headquarters": {"lat": 10.7892, "lon": 106.7018}
            }
        }

    def create_gui(self):
        """Tạo giao diện người dùng"""
        self.window = tk.Tk()
        self.window.title("Tra cứu địa chỉ số điện thoại - Việt Nam")
        self.window.geometry("1200x800")

        # Main container
        main_container = ttk.Frame(self.window, padding="10")
        main_container.pack(fill='both', expand=True)

        # Left panel
        left_panel = ttk.Frame(main_container)
        left_panel.pack(side='left', fill='y', padx=(0, 10))

        # Search section
        search_frame = ttk.LabelFrame(left_panel, text="Tìm kiếm", padding="10")
        search_frame.pack(fill='x', pady=(0, 10))

        # Phone number input
        ttk.Label(search_frame, text="Số điện thoại:").pack(anchor='w')
        self.phone_entry = ttk.Entry(search_frame, width=30)
        self.phone_entry.pack(fill='x', pady=5)

        # Region selection
        region_frame = ttk.LabelFrame(left_panel, text="Khu vực", padding="10")
        region_frame.pack(fill='both', expand=True)

        # Create notebook for regions and provinces
        self.region_notebook = ttk.Notebook(region_frame)
        self.region_notebook.pack(fill='both', expand=True)

        # Regions tab
        regions_tab = ttk.Frame(self.region_notebook)
        self.region_notebook.add(regions_tab, text="Vùng miền")

        # Region checkbuttons
        self.region_vars = {}
        for region in self.regions.keys():
            var = tk.BooleanVar(value=False)
            self.region_vars[region] = var
            ttk.Checkbutton(
                regions_tab,
                text=region,
                variable=var,
                command=self.update_province_list
            ).pack(anchor='w', pady=2)

        # Provinces tab
        provinces_tab = ttk.Frame(self.region_notebook)
        self.region_notebook.add(provinces_tab, text="Tỉnh thành")

        # Province listbox with scrollbar
        self.province_listbox = tk.Listbox(
            provinces_tab,
            selectmode='multiple',
            height=15
        )
        self.province_listbox.pack(side='left', fill='both', expand=True)
        
        scrollbar = ttk.Scrollbar(
            provinces_tab,
            orient='vertical',
            command=self.province_listbox.yview
        )
        scrollbar.pack(side='right', fill='y')
        self.province_listbox.config(yscrollcommand=scrollbar.set)

        # Search options
        options_frame = ttk.LabelFrame(left_panel, text="Tùy chọn tìm kiếm", padding="10")
        options_frame.pack(fill='x', pady=10)

        # Search method selection
        self.search_method = tk.StringVar(value="all")
        ttk.Radiobutton(
            options_frame,
            text="Tất cả phương pháp",
            value="all",
            variable=self.search_method
        ).pack(anchor='w')
        ttk.Radiobutton(
            options_frame,
            text="Chỉ dùng Google Maps",
            value="google",
            variable=self.search_method
        ).pack(anchor='w')
        ttk.Radiobutton(
            options_frame,
            text="Chỉ dùng OpenStreetMap",
            value="osm",
            variable=self.search_method
        ).pack(anchor='w')

        # Search button
        ttk.Button(
            left_panel,
            text="Tìm kiếm",
            command=self.search_location,
            style='Search.TButton'
        ).pack(fill='x', pady=10)

        # Right panel
        right_panel = ttk.Frame(main_container)
        right_panel.pack(side='right', fill='both', expand=True)

        # Results section
        results_frame = ttk.LabelFrame(right_panel, text="Kết quả", padding="10")
        results_frame.pack(fill='both', expand=True)

        # Results text widget
        self.result_text = tk.Text(
            results_frame,
            wrap='word',
            height=20,
            width=50
        )
        self.result_text.pack(fill='both', expand=True)
    def update_province_list(self):
        """Cập nhật danh sách tỉnh thành khi chọn vùng"""
        self.province_listbox.delete(0, tk.END)
        selected_regions = [
            region for region, var in self.region_vars.items() 
            if var.get()
        ]
        
        for region in selected_regions:
            for province in self.regions[region]["provinces"]:
                self.province_listbox.insert(tk.END, province["name"])

    def validate_phone(self, phone):
        """Kiểm tra số điện thoại hợp lệ"""
        phone = phone.replace(' ', '').replace('-', '')
        
        if phone.startswith('+84'):
            phone = '0' + phone[3:]
        elif phone.startswith('84'):
            phone = '0' + phone[2:]
            
        if not phone.isdigit() or len(phone) not in [10, 11]:
            return None
            
        # Kiểm tra đầu số
        for carrier, info in self.carriers.items():
            if phone[:3] in info["prefixes"]:
                return {
                    "number": phone,
                    "carrier": carrier,
                    "prefix": phone[:3]
                }
                
        return None

    def get_carrier_info(self, phone_data):
        """Lấy thông tin nhà mạng"""
        if not phone_data:
            return None
            
        carrier_name = phone_data["carrier"]
        carrier_info = self.carriers[carrier_name]
        
        return {
            "name": carrier_name,
            "mnc": carrier_info["mnc"],
            "coverage": carrier_info["coverage"],
            "headquarters": carrier_info["headquarters"]
        }

    def search_location(self):
        """Xử lý tìm kiếm vị trí"""
        # Lấy số điện thoại
        phone = self.phone_entry.get().strip()
        
        # Kiểm tra số điện thoại
        phone_data = self.validate_phone(phone)
        if not phone_data:
            messagebox.showerror(
                "Lỗi",
                "Số điện thoại không hợp lệ!\nVui lòng nhập số điện thoại đúng định dạng."
            )
            return

        # Kiểm tra vùng được chọn
        selected_indices = self.province_listbox.curselection()
        if not selected_indices:
            messagebox.showerror(
                "Lỗi",
                "Vui lòng chọn ít nhất một tỉnh thành để tìm kiếm!"
            )
            return

        # Lấy danh sách tỉnh được chọn
        selected_provinces = [
            self.province_listbox.get(i) for i in selected_indices
        ]

        # Hiển thị trạng thái đang tìm kiếm
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, "Đang tìm kiếm...\n")
        self.window.update()

        try:
            # Tìm kiếm vị trí
            locations = self.find_locations(phone_data, selected_provinces)
            
            if not locations:
                messagebox.showinfo(
                    "Thông báo",
                    "Không tìm thấy thông tin vị trí trong khu vực đã chọn!"
                )
                return

            # Hiển thị kết quả
            self.display_results(phone_data, locations)

        except Exception as e:
            messagebox.showerror("Lỗi", f"Có lỗi xảy ra: {str(e)}")

    def find_locations(self, phone_data, provinces):
        """Tìm vị trí dựa trên số điện thoại và tỉnh thành"""
        locations = []
        carrier_info = self.get_carrier_info(phone_data)

        for province_name in provinces:
            # Tìm thông tin tỉnh
            province_info = None
            for region in self.regions.values():
                for province in region["provinces"]:
                    if province["name"] == province_name:
                        province_info = province
                        break
                if province_info:
                    break

            if not province_info:
                continue

            # Tìm kiếm chi tiết qua Google Maps API
            try:
                details = self.get_location_details(
                    phone_data["number"],
                    province_info,
                    carrier_info
                )
                
                if details:
                    locations.append(details)
            except Exception as e:
                print(f"Lỗi khi tìm chi tiết cho {province_name}: {str(e)}")

        return locations
    def get_from_cache(self, phone):
        """Lấy thông tin từ cache"""
        try:
            self.cursor.execute('''
                SELECT location_data FROM location_cache 
                WHERE phone_number = ? AND expires_at > datetime('now')
            ''', (phone,))
            result = self.cursor.fetchone()
            if result:
                return json.loads(result[0])
        except Exception as e:
            print(f"Lỗi khi đọc cache: {str(e)}")
        return None
    
    def save_to_cache(self, phone, location_data):
        """Lưu thông tin vào cache"""
        try:
            expires_at = datetime.now().replace(hour=23, minute=59, second=59)
            self.cursor.execute('''
                INSERT OR REPLACE INTO location_cache 
                (phone_number, location_data, timestamp, expires_at)
                VALUES (?, ?, datetime('now'), ?)
            ''', (phone, json.dumps(location_data), expires_at))
            self.conn.commit()
        except Exception as e:
            print(f"Lỗi khi lưu cache: {str(e)}")
    def get_location_details(self, phone, province, carrier):
        """Lấy thông tin chi tiết về vị trí"""
        try:
            # 1. Trước tiên thử tìm từ database cache
            cache_result = self.get_from_cache(phone)
            if cache_result:
                return cache_result
    
            # 2. Sử dụng Google Places API để tìm địa điểm chi tiết
            places_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
            
            # Tạo query chi tiết hơn bằng cách kết hợp nhiều thông tin
            search_query = f"{province['name']}, Vietnam"
            
            params = {
                'query': search_query,
                'key': self.google_maps_api_key,
                'language': 'vi',
                'region': 'VN'
            }
            
            response = self.session.get(places_url, params=params)
            if response.status_code == 200:
                data = response.json()
                if data['status'] == 'OK' and data['results']:
                    place = data['results'][0]
                    
                    # 3. Lấy thêm chi tiết về địa điểm
                    place_id = place['place_id']
                    details_url = "https://maps.googleapis.com/maps/api/place/details/json"
                    details_params = {
                        'place_id': place_id,
                        'key': self.google_maps_api_key,
                        'language': 'vi',
                        'fields': 'address_component,formatted_address,geometry,name,vicinity'
                    }
                    
                    details_response = self.session.get(details_url, params=details_params)
                    if details_response.status_code == 200:
                        details_data = details_response.json()
                        if details_data['status'] == 'OK':
                            result = details_data['result']
                            
                            # Tạo kết quả chi tiết
                            location_result = {
                                'province': province["name"],
                                'formatted_address': result.get('formatted_address', ''),
                                'lat': result['geometry']['location']['lat'],
                                'lng': result['geometry']['location']['lng'],
                                'place_id': place_id,
                                'components': self.parse_address_components(result.get('address_components', [])),
                                'vicinity': result.get('vicinity', ''),
                                'accuracy': 'high'
                            }
                            
                            # Lưu vào cache
                            self.save_to_cache(phone, location_result)
                            
                            return location_result
    
            # 4. Nếu không tìm được qua Google Places, sử dụng Geocoding
            geocode_url = "https://maps.googleapis.com/maps/api/geocode/json"
            geocode_params = {
                'address': f"{province['name']}, Vietnam",
                'key': self.google_maps_api_key,
                'language': 'vi'
            }
            
            geocode_response = self.session.get(geocode_url, params=geocode_params)
            if geocode_response.status_code == 200:
                geocode_data = geocode_response.json()
                if geocode_data['status'] == 'OK':
                    result = geocode_data['results'][0]
                    
                    location_result = {
                        'province': province["name"],
                        'formatted_address': result['formatted_address'],
                        'lat': result['geometry']['location']['lat'],
                        'lng': result['geometry']['location']['lng'],
                        'place_id': result.get('place_id', ''),
                        'components': self.parse_address_components(result['address_components']),
                        'accuracy': 'medium'
                    }
                    
                    # Lưu vào cache
                    self.save_to_cache(phone, location_result)
                    
                    return location_result
                        
        except Exception as e:
            print(f"Lỗi khi lấy chi tiết vị trí: {str(e)}")
            
        # 5. Nếu mọi cách đều thất bại, trả về thông tin cơ bản
        return {
            'province': province["name"],
            'formatted_address': f"{province['name']}, Vietnam",
            'lat': province['lat'],
            'lng': province['lon'],
            'components': {
                'street_number': '',
                'route': '',
                'ward': '',
                'district': '',
                'city': province["name"],
                'province': province["name"],
                'country': 'Vietnam'
            },
            'accuracy': 'low'
        }

    def parse_address_components(self, components):
        """Phân tích các thành phần địa chỉ"""
        result = {
            'street_number': '',
            'route': '',
            'ward': '',
            'district': '',
            'city': '',
            'province': '',
            'country': ''
        }
        
        for component in components:
            types = component['types']
            if 'street_number' in types:
                result['street_number'] = component['long_name']
            elif 'route' in types:
                result['route'] = component['long_name']
            elif 'administrative_area_level_3' in types:
                result['ward'] = component['long_name']
            elif 'administrative_area_level_2' in types:
                result['district'] = component['long_name']
            elif 'administrative_area_level_1' in types:
                result['city'] = component['long_name']
            elif 'locality' in types:
                result['province'] = component['long_name']
            elif 'country' in types:
                result['country'] = component['long_name']
                
        return result

    def display_results(self, phone_data, locations):
        """Hiển thị kết quả tìm kiếm"""
        self.result_text.delete(1.0, tk.END)
        
        # Hiển thị thông tin tổng quan
        carrier_info = self.get_carrier_info(phone_data)
        summary = f"""=== THÔNG TIN TÌM KIẾM ===
Số điện thoại: {phone_data['number']}
Nhà mạng: {carrier_info['name']}
Vùng phủ sóng: {carrier_info['coverage']}
Thời gian: {self.current_time}
Số vị trí tìm thấy: {len(locations)}

=== KẾT QUẢ CHI TIẾT ===\n"""
        self.result_text.insert(tk.END, summary)

        # Tạo bản đồ
        center_lat = sum(loc['lat'] for loc in locations) / len(locations)
        center_lng = sum(loc['lng'] for loc in locations) / len(locations)

        m = folium.Map(
            location=[center_lat, center_lng],
            zoom_start=6,
            tiles='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
            attr='OpenStreetMap'
        )

        # Thêm vị trí nhà mạng
        hq = carrier_info['headquarters']
        folium.Marker(
            [hq['lat'], hq['lon']],
            popup=f"Trụ sở {carrier_info['name']}",
            icon=folium.Icon(color='green', icon='info-sign')
        ).add_to(m)

        # Thêm các vị trí tìm thấy
        for idx, loc in enumerate(locations, 1):
            # Tạo popup content
            popup_content = f"""
            <div style="width:300px">
                <h4>{loc['province']}</h4>
                <p><b>Địa chỉ:</b> {loc['formatted_address']}</p>
                <p><b>Quận/Huyện:</b> {loc['components']['district']}</p>
                <p><b>Phường/Xã:</b> {loc['components']['ward']}</p>
                <p><b>Tọa độ:</b> {loc['lat']:.6f}, {loc['lng']:.6f}</p>
            </div>
            """
            
            # Thêm marker
            folium.Marker(
                [loc['lat'], loc['lng']],
                popup=folium.Popup(popup_content, max_width=350),
                icon=folium.Icon(color='red', icon='info-sign')
            ).add_to(m)

            # Thêm vòng tròn phủ sóng
            folium.Circle(
                [loc['lat'], loc['lng']],
                radius=5000,  # 5km
                color='red',
                fill=True,
                popup=f'Phạm vi phủ sóng - {loc["province"]}'
            ).add_to(m)

            # Hiển thị thông tin trong kết quả
            location_info = f"""
Vị trí {idx}:
• Tỉnh/Thành phố: {loc['province']}
• Địa chỉ: {loc['formatted_address']}
• Quận/Huyện: {loc['components']['district']}
• Phường/Xã: {loc['components']['ward']}
• Tọa độ: {loc['lat']:.6f}, {loc['lng']:.6f}
"""
            self.result_text.insert(tk.END, location_info)

        # Thêm các control cho bản đồ
        folium.LayerControl().add_to(m)
        plugins.Fullscreen().add_to(m)
        plugins.MiniMap().add_to(m)
        plugins.MousePosition().add_to(m)

        # Lưu và mở bản đồ
        map_file = f"phone_location_{self.current_time.strftime('%Y%m%d_%H%M%S')}.html"
        m.save(map_file)
        webbrowser.open('file://' + os.path.realpath(map_file))

        # Lưu vào database
        self.save_to_history(phone_data, locations)

    def save_to_history(self, phone_data, locations):
        """Lưu lịch sử tìm kiếm vào database"""
        try:
            for location in locations:
                self.cursor.execute('''
                    INSERT INTO search_history 
                    (phone_number, carrier, region, province, district, ward,
                     full_address, latitude, longitude, timestamp, user_id,
                     search_method)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    phone_data['number'],
                    phone_data['carrier'],
                    self.get_region_by_province(location['province']),
                    location['province'],
                    location['components']['district'],
                    location['components']['ward'],
                    location['formatted_address'],
                    location['lat'],
                    location['lng'],
                    self.current_time,
                    self.current_user,
                    self.search_method.get()
                ))
            self.conn.commit()
        except Exception as e:
            print(f"Lỗi khi lưu lịch sử: {str(e)}")

    def get_region_by_province(self, province_name):
        """Lấy tên vùng từ tên tỉnh"""
        for region_name, region_data in self.regions.items():
            for province in region_data["provinces"]:
                if province["name"] == province_name:
                    return region_name
        return "Không xác định"

    def run(self):
        """Chạy ứng dụng"""
        self.window.mainloop()

if __name__ == "__main__":
    app = PhoneLocationFinder()
    app.run()