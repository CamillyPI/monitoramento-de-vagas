import network
import time
import ubinascii
from machine import Pin, unique_id
from umqtt.simple import MQTTClient

# WIFI PADRAO
WIFI_SSID = "Wokwi-GUEST"
WIFI_PASS = ""

# MQTT (BROKER PUBLICO)
MQTT_HOST = "broker.hivemq.com"
MQTT_CLIENT_ID = ubinascii.hexlify(unique_id())
TOP_ALERTA = "condominio/garagem/alertas"


led_verde = Pin(2, Pin.OUT)
led_vermelho = Pin(4, Pin.OUT)
botao = Pin(13, Pin.IN, Pin.PULL_UP)

# REGRAS DA VAGA
VAGA_ID = "303A"
VAGA_TIPO = "simples" # "simples" ou "dupla"

CARROS = [
    {"tag": "TAG-303A", "vagas": "303A"},
    {"tag": "TAG-303B", "vagas": "303A|303B"},
    {"tag": "TAG-404B", "vagas": "404B"}
]

idx_carro = 0
n_carros = len(CARROS)


def contem_vaga(lista_str, vaga_alvo):
    # Verifica se vaga_alvo ta na string lista_str
    return vaga_alvo in lista_str.split('|')

def autorizado(vaga_id, tipo, tag):
    # Busca as permissoes da tag
    vagas_permitidas = None
    for carro in CARROS:
        if carro["tag"] == tag:
            vagas_permitidas = carro["vagas"]
            break
    
    if not vagas_permitidas:
        return False
        
    if tipo == "simples":
        return vagas_permitidas == vaga_id
    else:
        return contem_vaga(vagas_permitidas, vaga_id)


# CONECTANDO
def conecta_wifi():
    print("Conectando ao WiFi", end="")
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASS)
    
    while not wlan.isconnected():
        print(".", end="")
        time.sleep(0.25)
    print("\nWiFi Conectado!")
    return wlan

def conecta_mqtt():
    client = MQTTClient(MQTT_CLIENT_ID, MQTT_HOST)
    client.connect()
    print("MQTT Conectado!")
    return client



def publica_alerta_se_errado(client, tag, ok):
    if ok:
        return 

    payload = '{"vaga_id":"' + VAGA_ID + '", "tag":"' + tag + '", "status":"ERRADO", "motivo":"vaga incorreta"}'
    
    try:
        client.publish(TOP_ALERTA, payload)
        print(f"[ALERTA MQTT] {payload}")
    except OSError:
        print("Erro ao publicar MQTT")

def atualiza_leds_e_publica(client, tag):
    ok = autorizado(VAGA_ID, VAGA_TIPO, tag)
    
    if ok:
        led_verde.value(1)
        led_vermelho.value(0)
        status_txt = "OK (VERDE)"
    else:
        led_verde.value(0)
        led_vermelho.value(1)
        status_txt = "ERRADO (VERMELHO)"
    
    publica_alerta_se_errado(client, tag, ok)
    
    print(f"TAG: {tag} | Status: {status_txt}")

# LOOP
def main():
    conecta_wifi()
    try:
        client = conecta_mqtt()
    except:
        print("Falha inicial no MQTT... tentando reconectar no loop")
        client = None

    global idx_carro
    
    # Estado anterior do botao para detectar o clique
    prev_btn = 1 
    
    # Validando
    if client:
        atualiza_leds_e_publica(client, CARROS[idx_carro]["tag"])

    while True:
        if client:
            try:
                client.check_msg()
            except OSError:
                print("Reconectando MQTT...")
                try:
                    client = conecta_mqtt()
                except:
                    pass
        
        now_btn = botao.value()
        
        if prev_btn == 1 and now_btn == 0:
            idx_carro = (idx_carro + 1) % n_carros
            tag_atual = CARROS[idx_carro]["tag"]
            
            if client:
                atualiza_leds_e_publica(client, tag_atual)
            
            time.sleep(0.2)
            
        prev_btn = now_btn
        time.sleep(0.05)


if __name__ == "__main__":
    main()