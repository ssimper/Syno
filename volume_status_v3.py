import getopt, json, pprint, requests, sys


class Authentication:
    def __init__(
        self, ip_address, port, username, password, secure=False,
        cert_verify=False, dsm_version=6, debug=True, otp_code=None
        ):
        self._ip_address = ip_address
        self._port = port
        self._username = username
        self._password = password
        self._sid = None
        self._session_expire = True
        self._verify = cert_verify
        self._version = dsm_version
        self._debug = debug
        self._otp_code = otp_code
        schema = 'https' if secure else 'http'
        self._base_url = f'{schema}://{self._ip_address}:{self._port}/webapi/'
        self.full_api_list = {}
        self.app_api_list = {}


    def login(self, application):
        #Connect to NAS and get SID for other requests
        login_api = 'auth.cgi?api=SYNO.API.Auth'
        param = {
            'version': self._version, 'method': 'login',
            'account': self._username, 'passwd': self._password,
            'session': application, 'format': 'sid'
        }
        if self._otp_code:
            param['otp_code'] = self._otp_code

        if not self._session_expire:
            if self._sid is not None:
                self._session_expire = False
                if self._debug is True:
                    return 'User already logged'
        else:
            full_param = (self._base_url + login_api, param)
            session_request = requests.get(
                self._base_url + login_api, param, verify=self._verify
            )
            my_output = session_request.json()
            self._sid = session_request.json()['data']['sid']
            self._session_expire = False
            if self._debug is True:
                print('User logging... New session started!')
                return self._sid

    def logout(self, application):
        logout_api = 'auth.cgi?api=SYNO.API.Auth'
        param = {'version': '2', 'method': 'logout', 'session': application}

        response = requests.get(
            self._base_url + logout_api, param, verify=self._verify
        )
        if response.json()['success'] is True:
            self._session_expire = True
            self._sid = None
            if self._debug is True:
                print("Logged out")
                return 'Logged out'
        else:
            self._session_expire = True
            self._sid = None
            if self._debug is True:
                print("No valid session is open")
                return 'No valid session is open'

    
    def find_nas_name(self, api_dico, my_sid):
        api_name = 'SYNO.FileStation.Info'
        info = api_dico[api_name]
        api_path = info['path']
        full_params = (
            f"{self._base_url}{api_path}?api={api_name}"
            f"&version={info['minVersion']}&method=get&_sid={my_sid}"
        )
        response = requests.get(full_params)
        response_dico = response.json()
        nas_name = response_dico['data']['hostname']
        #print(f"info : {info}, api_path : {api_path}, full_params : {full_params}, response_dico : {response_dico}")
        return nas_name
    

    def show_volume_status(self, api_dico, my_sid, my_method):
        api_name = 'SYNO.Storage.CGI.Storage'
        info = api_dico[api_name]
        api_path = info['path']
        full_params = (
            f"{self._base_url}{api_path}?api={api_name}"
            f"&version={info['minVersion']}&method={my_method}&_sid={my_sid}"
        )
        response = requests.get(full_params)
        response_dico = response.json()
        #print(f"info : {info}, api_path : {api_path}, full_params : {full_params}")
        disks_info = response_dico['data']['disks']
        disks_dico = {}
        current_disk = {}
        volumes_dico = {}
        current_volume = {}
        for disk_info in disks_info:
            current_disk['Disk position'] = disk_info['longName']
            current_disk['Vendor'] = disk_info['vendor']
            current_disk['Model'] = disk_info['model']
            current_disk['Serial'] = disk_info['serial']
            current_disk['Status'] = disk_info['overview_status']
            current_disk['Total size'] = int(disk_info['size_total'])
            disks_dico[current_disk['Disk position']] = current_disk
            current_disk = {}
        #print("current dico :", disks_dico)
        volumes_info = response_dico['data']['volumes']
        for volume_info in volumes_info:
            try:
                volume_info['vol_desc']
            except KeyError:
                #print('on utilise desc')
                volume_description = 'desc'
            else:
                volume_description = 'vol_desc'
            current_volume['Volume description'] = volume_info[volume_description]
            current_volume['Volume path'] = volume_info['vol_path']
            current_volume['Volume size'] = int(volume_info['size']['total'])
            current_volume['Volume used'] = int(volume_info['size']['used'])
            current_volume['Volume used(%)'] = round (
                (
                current_volume['Volume used']/current_volume['Volume size'] * 100
                ),2
            )
            volumes_dico[current_volume['Volume description']] = current_volume
            current_volume = {}
            #print(volumes_dico)
            #print(len(str(volumes_dico['Volume used'])))

        return disks_dico, volumes_dico
        #print(response_dico['data']['disks'][0]['model'])

    
    def get_api_list(self, app=None):
        query_path = 'query.cgi?api=SYNO.API.Info'
        list_query = {'version': '1', 'method': 'query', 'query': 'all'}

        response = requests.get(
            self._base_url + query_path, list_query, verify=self._verify
        ).json()
        if app is not None:
            for key in response['data']:
                if app.lower() in key.lower():
                    self.app_api_list[key] = response['data'][key]
        else:
            self.full_api_list = response['data']
            return self.full_api_list

        return



def main():
    nas_ip = None
    nas_port = 5000
    nas_login = None
    nas_pwd = None
    argv = sys.argv[1:]
    try:
        opts, args = getopt.getopt(
            argv, "i:u:p:", [
                "ip=", "user=", "password="
            ]
        )
    except:
        print("Erreur ...")
    
    for opt, arg in opts:
        if opt in ['-i', '--ip']:
            nas_ip = arg
        elif opt in ['-u', '--user']:
            nas_login = arg
        elif opt in ['-p', '--password']:
            nas_pwd = arg
    #Create object
    test = Authentication(nas_ip, nas_port, nas_login, nas_pwd)
    #Connect to NAS
    my_sid = test.login('toto')
    #Retrieve list of API in a dictionary
    api_dico = test.get_api_list()
    nas_name = test.find_nas_name(api_dico, my_sid)
    print(nas_name)
    disks_info, volume_info = test.show_volume_status(
        api_dico, my_sid, my_method="load_info"
        )
    for value in disks_info.values():
        for k, v in value.items():
            print(k, v)
        print("*****")
    print(nas_name)
    for value in volume_info.items():
        v_size = value[1]['Volume size']
        u_size = value[1]['Volume used']
        percent_size = value[1]['Volume used(%)']
        if len(str(v_size)) > 12:
            v_size /= (10**12)
            v_unit = "To"
        elif len(str(v_size)) > 9:
            v_size /= 10**9
            v_unit = "Go"
        else:
            v_size /= 10**6
            v_unit = "Mo"
        if len(str(u_size)) > 12:
            u_size /= (10**12)
            u_unit = "To"
        elif len(str(u_size)) > 9:
            u_size /= 10**9
            u_unit = "Go"
        else:
            u_size /= 10**6
            u_unit = "Mo"
        print(
            f"Nom du volume : {value[1]['Volume description']}\n"
            f"Point de montage : {value[1]['Volume path']}\n"
            f"Taille du volume : {round(v_size, 2)} {v_unit}\n"
            f"Taille utilisée : {round(u_size,2)} {u_unit}\n"
            f"Taille utilisée (%) : {percent_size}%"
        )
    # v_size = volume_info['Volume size']
    # u_size = volume_info['Volume used']
    # percent_size = volume_info['Volume used(%)']
    # if len(str(v_size)) > 12:
    #     v_size /= (10**12)
    #     v_unit = "To"
    # elif len(str(v_size)) > 9:
    #     v_size /= 10**9
    #     v_unit = "Go"
    # if len(str(u_size)) > 12:
    #     u_size /= (10**12)
    #     u_unit = "To"
    # elif len(str(u_size)) > 9:
    #     u_size /= 10**9
    #     u_unit = "Go"
    # print(
    #     f"Nom du volume : {volume_info['Volume description']}\n"
    #     f"Point de montage : {volume_info['Volume path']}\n"
    #     f"Taille du volume : {round(v_size, 2)} {v_unit}\n"
    #     f"Taille utilisée : {round(u_size, 2)} {u_unit}\n"
    #     f"Pourcentage utilisé : {percent_size}%"
    #)
    #Log out
    test.logout('toto')


if __name__ == '__main__':
    main()
