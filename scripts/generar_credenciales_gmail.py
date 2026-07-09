"""
Genera las credenciales OAuth de Gmail (client_id, client_secret, refresh_token)
para el monitor de correo de AeroTrack Travel (CU-O41).

Este script se corre UNA SOLA VEZ, de forma manual, para autorizar la bandeja
dedicada de la agencia (ej. aerotracktravel.demo@gmail.com). El refresh_token
que produce es el que luego usa el sistema (FastAPI/Airflow) de forma
automática e indefinida, sin volver a pedir login.

Requisitos previos:
1. pip install google-auth-oauthlib google-api-python-client --break-system-packages
2. Haber descargado client_secret.json desde Google Cloud Console
   (APIs & Services -> Credentials -> tu OAuth Client ID tipo "Desktop app"
   -> ícono de descarga -> guardar como client_secret.json)
3. Colocar ese archivo en la misma carpeta que este script

Cómo correrlo:
    python generar_credenciales_gmail.py

Qué vas a ver:
- Se abre tu navegador automáticamente en localhost.
- IMPORTANTE: inicia sesión con la cuenta DEDICADA de la agencia
  (ej. aerotracktravel.demo@gmail.com), NO con tu cuenta personal.
  Si el navegador ya tiene otra cuenta logueada, usa una ventana de
  incógnito o cierra sesión primero.
- Si aparece "Google no verificó esta app": clic en "Avanzado" ->
  "Ir a [nombre de tu app] (no seguro)". Es normal y seguro, es tu propia app.
- Acepta el permiso de lectura de Gmail solicitado.
- El script imprime client_id, client_secret y refresh_token al final —
  cópialos directo a tu .env.
"""

from google_auth_oauthlib.flow import InstalledAppFlow

# Alcance de SOLO LECTURA — suficiente para monitorear avisos de aerolíneas.
# No se pide permiso de envío/modificación, siguiendo el principio de
# minimización de la constitución (Sección B2).
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


def main():
    flow = InstalledAppFlow.from_client_secrets_file(
        'client_secret.json',
        scopes=SCOPES,
    )

    # prompt='consent' + access_type='offline' fuerzan que Google entregue
    # un refresh_token incluso si ya habías autorizado esta app antes.
    credentials = flow.run_local_server(
        port=0,
        prompt='consent',
        access_type='offline',
    )

    print("\n" + "=" * 60)
    print("Copia estos valores a tu archivo .env:")
    print("=" * 60)
    print(f"GMAIL_CLIENT_ID={credentials.client_id}")
    print(f"GMAIL_CLIENT_SECRET={credentials.client_secret}")
    print(f"GMAIL_REFRESH_TOKEN={credentials.refresh_token}")
    print("=" * 60)

    if not credentials.refresh_token:
        print("\n⚠️  No se recibió refresh_token.")
        print("   Esto pasa si ya habías autorizado esta app antes y Google")
        print("   no emite uno nuevo automáticamente. Solución:")
        print("   1. Ve a https://myaccount.google.com/permissions")
        print("      (logueada como la cuenta dedicada de la agencia)")
        print("   2. Busca tu app y revoca el acceso")
        print("   3. Vuelve a correr este script")


if __name__ == '__main__':
    main()
