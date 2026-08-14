import json
import uuid
import requests
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse


class ThreeXUI:

    def __init__(
        self,
        base_url,
        username,
        password,
        api_token=""
    ):

        self.base_url = (
            str(base_url or "")
            .rstrip("/")
        )

        self.username = username
        self.password = password
        self.api_token = api_token

        self.session = requests.Session()

        self.session.headers.update({
            "User-Agent": "V2Ray-Podda-Store/1.0"
        })

    # =====================================================
    # URL
    # =====================================================

    def url(self, path):

        return (
            self.base_url
            + "/"
            + path.lstrip("/")
        )

    # =====================================================
    # REQUEST
    # =====================================================

    def request(
        self,
        method,
        path,
        **kwargs
    ):

        headers = kwargs.pop(
            "headers",
            {}
        )

        if self.api_token:

            headers[
                "Authorization"
            ] = f"Bearer {self.api_token}"

        response = self.session.request(
            method=method,
            url=self.url(path),
            headers=headers,
            timeout=30,
            **kwargs
        )

        if response.status_code >= 400:

            raise Exception(
                f"HTTP {response.status_code}: "
                f"{response.text[:1000]}"
            )

        try:

            return response.json()

        except Exception:

            return {
                "success": True,
                "raw": response.text
            }

    # =====================================================
    # LOGIN
    # =====================================================

    def login(self):

        if self.api_token:

            return True, "API token configured"

        try:

            response = self.session.post(
                self.url("/login"),
                data={
                    "username": self.username,
                    "password": self.password
                },
                timeout=30
            )

            if response.status_code != 200:

                return (
                    False,
                    f"HTTP {response.status_code}: "
                    f"{response.text[:500]}"
                )

            try:

                data = response.json()

            except Exception:

                data = {}

            if data.get("success") is False:

                return (
                    False,
                    data.get(
                        "msg",
                        "Login failed"
                    )
                )

            return (
                True,
                data.get(
                    "msg",
                    "Login successful"
                )
            )

        except Exception as e:

            return False, str(e)

    # =====================================================
    # TEST
    # =====================================================

    def test_connection(self):

        ok, message = self.login()

        if not ok:

            return False, message

        try:

            result = self.request(
                "GET",
                "/panel/api/inbounds/list"
            )

            if result.get("success") is False:

                return (
                    False,
                    result.get(
                        "msg",
                        "API request failed"
                    )
                )

            return True, "3X-UI connected successfully"

        except Exception as e:

            return False, str(e)

    # =====================================================
    # LIST INBOUNDS
    # =====================================================

    def list_inbounds(self):

        ok, message = self.login()

        if not ok:
            raise Exception(message)

        result = self.request(
            "GET",
            "/panel/api/inbounds/list"
        )

        if result.get("success") is False:

            raise Exception(
                result.get(
                    "msg",
                    "Could not load inbounds"
                )
            )

        obj = result.get(
            "obj",
            []
        )

        if not isinstance(obj, list):

            return []

        output = []

        for inbound in obj:

            if not isinstance(
                inbound,
                dict
            ):
                continue

            output.append(
                self.normalize_inbound(
                    inbound
                )
            )

        return output

    # =====================================================
    # NORMALIZE INBOUND
    # =====================================================

    def normalize_inbound(
        self,
        inbound
    ):

        settings = inbound.get(
            "settings",
            {}
        )

        stream = inbound.get(
            "streamSettings",
            {}
        )

        if isinstance(
            settings,
            str
        ):

            try:
                settings = json.loads(
                    settings
                )
            except Exception:
                settings = {}

        if isinstance(
            stream,
            str
        ):

            try:
                stream = json.loads(
                    stream
                )
            except Exception:
                stream = {}

        return {
            "id": inbound.get("id"),
            "remark": inbound.get(
                "remark",
                ""
            ),
            "protocol": inbound.get(
                "protocol",
                ""
            ),
            "port": inbound.get(
                "port"
            ),
            "listen": inbound.get(
                "listen",
                ""
            ),
            "enable": inbound.get(
                "enable",
                True
            ),
            "expiryTime": inbound.get(
                "expiryTime",
                0
            ),
            "total": inbound.get(
                "total",
                0
            ),
            "settings": settings,
            "streamSettings": stream,
            "raw": inbound
        }

    # =====================================================
    # GET INBOUND
    # =====================================================

    def get_inbound(
        self,
        inbound_id
    ):

        ok, message = self.login()

        if not ok:
            raise Exception(message)

        result = self.request(
            "GET",
            f"/panel/api/inbounds/get/{int(inbound_id)}"
        )

        if result.get("success") is False:

            raise Exception(
                result.get(
                    "msg",
                    "Inbound request failed"
                )
            )

        obj = result.get(
            "obj"
        )

        if not obj:
            return None

        return self.normalize_inbound(
            obj
        )

    # =====================================================
    # ADD CLIENT
    # =====================================================

    def create_client(
        self,
        inbound_id,
        email,
        expiry_ms,
        traffic_gb,
        telegram_id=0
    ):

        ok, message = self.login()

        if not ok:
            return False, message

        inbound = self.get_inbound(
            inbound_id
        )

        if not inbound:

            return False, "Inbound not found"

        protocol = str(
            inbound.get(
                "protocol",
                ""
            )
        ).lower()

        client_uuid = str(
            uuid.uuid4()
        )

        total_bytes = int(
            max(
                0,
                float(traffic_gb)
            )
            * 1024
            * 1024
            * 1024
        )

        client = {
            "email": str(email),
            "enable": True,
            "expiryTime": int(expiry_ms),
            "totalGB": total_bytes,
            "tgId": int(telegram_id or 0)
        }

        if protocol in (
            "vless",
            "vmess"
        ):

            client["id"] = client_uuid

        elif protocol == "trojan":

            client["password"] = client_uuid

        elif protocol == "shadowsocks":

            client["password"] = client_uuid

        else:

            client["id"] = client_uuid

        # Current 3X-UI client API
        try:

            result = self.request(
                "POST",
                "/panel/api/clients/add",
                json={
                    "client": client,
                    "inboundIds": [
                        int(inbound_id)
                    ]
                }
            )

            if result.get("success"):

                return True, {
                    "id": client_uuid,
                    "uuid": client_uuid,
                    "client": client,
                    "response": result
                }

            # fallback old API
        except Exception:
            pass

        # Old-compatible endpoint
        settings = inbound.get(
            "settings",
            {}
        )

        if not isinstance(
            settings,
            dict
        ):
            settings = {}

        old_client = dict(client)

        payload = {
            "id": int(inbound_id),
            "settings": json.dumps({
                "clients": [
                    old_client
                ]
            })
        }

        try:

            result = self.request(
                "POST",
                "/panel/api/inbounds/addClient",
                json=payload
            )

            if result.get("success"):

                return True, {
                    "id": client_uuid,
                    "uuid": client_uuid,
                    "client": client,
                    "response": result
                }

            return False, result.get(
                "msg",
                "Client creation failed"
            )

        except Exception as e:

            return False, str(e)

    # =====================================================
    # GET CLIENT
    # =====================================================

    def get_client(
        self,
        email
    ):

        ok, message = self.login()

        if not ok:
            return False, message

        try:

            result = self.request(
                "GET",
                "/panel/api/clients/get/"
                + requests.utils.quote(
                    str(email),
                    safe=""
                )
            )

            if result.get("success") is False:

                return False, result.get(
                    "msg",
                    "Client not found"
                )

            return True, result.get(
                "obj"
            )

        except Exception as e:

            return False, str(e)

    # =====================================================
    # GET CLIENT LINKS
    # =====================================================

    def get_client_links(
        self,
        email
    ):

        ok, message = self.login()

        if not ok:
            return False, message

        ok_client, client_obj = (
            self.get_client(email)
        )

        if not ok_client:

            return False, client_obj

        links = []

        if isinstance(
            client_obj,
            dict
        ):

            external = client_obj.get(
                "externalLinks",
                []
            )

            if isinstance(
                external,
                list
            ):

                for item in external:

                    if isinstance(
                        item,
                        dict
                    ):

                        value = item.get(
                            "value"
                        )

                        if isinstance(
                            value,
                            str
                        ) and value.startswith(
                            (
                                "vless://",
                                "vmess://",
                                "trojan://",
                                "ss://"
                            )
                        ):

                            links.append(
                                value
                            )

                    elif isinstance(
                        item,
                        str
                    ):

                        links.append(item)

            # Sometimes client object contains links
            for key in (
                "links",
                "link",
                "externalLink"
            ):

                value = client_obj.get(
                    key
                )

                if isinstance(
                    value,
                    str
                ):

                    links.append(value)

                elif isinstance(
                    value,
                    list
                ):

                    links.extend(value)

        # Old inbound method
        if not links:

            inbound_ids = []

            if isinstance(
                client_obj,
                dict
            ):

                inbound_ids = client_obj.get(
                    "inboundIds",
                    []
                )

            if not inbound_ids:

                return True, []

            for inbound_id in inbound_ids:

                inbound = self.get_inbound(
                    inbound_id
                )

                if not inbound:
                    continue

                found = self.build_client_link(
                    inbound,
                    email,
                    client_obj
                )

                if found:
                    links.append(found)

        # remove duplicates
        clean = []

        for link in links:

            if not isinstance(
                link,
                str
            ):
                continue

            if link not in clean:
                clean.append(link)

        return True, clean

    # =====================================================
    # BUILD LINK
    # =====================================================

    def build_client_link(
        self,
        inbound,
        email,
        client_obj=None
    ):

        protocol = str(
            inbound.get(
                "protocol",
                ""
            )
        ).lower()

        settings = inbound.get(
            "settings",
            {}
        )

        stream = inbound.get(
            "streamSettings",
            {}
        )

        if not isinstance(
            settings,
            dict
        ):
            settings = {}

        if not isinstance(
            stream,
            dict
        ):
            stream = {}

        clients = settings.get(
            "clients",
            []
        )

        target = None

        for client in clients:

            if not isinstance(
                client,
                dict
            ):
                continue

            if str(
                client.get("email", "")
            ).lower() == str(
                email
            ).lower():

                target = client
                break

        if not target:
            return None

        client_id = (
            target.get("id")
            or target.get("uuid")
        )

        if not client_id:
            return None

        parsed = urlparse(
            self.base_url
        )

        host = (
            parsed.hostname
            or ""
        )

        port = inbound.get(
            "port"
        )

        if not host or not port:
            return None

        network = stream.get(
            "network",
            "tcp"
        )

        security = stream.get(
            "security",
            "none"
        )

        params = {
            "type": network,
            "security": security
        }

        if network == "ws":

            ws = stream.get(
                "wsSettings",
                {}
            )

            if isinstance(
                ws,
                dict
            ):

                if ws.get("path"):
                    params["path"] = ws["path"]

                headers = ws.get(
                    "headers",
                    {}
                )

                if isinstance(
                    headers,
                    dict
                ) and headers.get("Host"):

                    params["host"] = (
                        headers["Host"]
                    )

        if network == "grpc":

            grpc = stream.get(
                "grpcSettings",
                {}
            )

            if isinstance(
                grpc,
                dict
            ) and grpc.get(
                "serviceName"
            ):

                params[
                    "serviceName"
                ] = grpc[
                    "serviceName"
                ]

        if security == "reality":

            reality = stream.get(
                "realitySettings",
                {}
            )

            if isinstance(
                reality,
                dict
            ):

                settings2 = reality.get(
                    "settings",
                    {}
                )

                if isinstance(
                    settings2,
                    dict
                ):

                    if settings2.get(
                        "publicKey"
                    ):

                        params["pbk"] = (
                            settings2[
                                "publicKey"
                            ]
                        )

                    if settings2.get(
                        "fingerprint"
                    ):

                        params["fp"] = (
                            settings2[
                                "fingerprint"
                            ]
                        )

                if reality.get("serverName"):

                    params["sni"] = (
                        reality[
                            "serverName"
                        ]
                    )

        query = urlencode(
            params
        )

        return (
            f"{protocol}://"
            f"{client_id}@"
            f"{host}:{port}"
            f"?{query}"
            f"#{email}"
        )

    # =====================================================
    # CLIENT FROM INBOUND
    # =====================================================

    def get_client_from_inbound(
        self,
        inbound,
        email
    ):

        if not inbound:
            return None

        settings = inbound.get(
            "settings",
            {}
        )

        if not isinstance(
            settings,
            dict
        ):
            return None

        clients = settings.get(
            "clients",
            []
        )

        for client in clients:

            if not isinstance(
                client,
                dict
            ):
                continue

            if str(
                client.get("email", "")
            ).lower() == str(
                email
            ).lower():

                return client

        return None


# =========================================================
# SNI
# =========================================================

def apply_sni(
    link,
    sni
):

    if not link:
        return link

    if not sni:
        return link

    try:

        parsed = urlparse(
            link
        )

        query = parse_qs(
            parsed.query,
            keep_blank_values=True
        )

        query["sni"] = [
            str(sni)
        ]

        new_query = urlencode(
            query,
            doseq=True
        )

        return urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment
        ))

    except Exception:

        return link


if __name__ == "__main__":

    print("3X-UI panel module loaded.")