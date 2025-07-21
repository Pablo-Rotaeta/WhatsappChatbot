# whatsapp_bot.py (script principal)
import argparse
from modules.scheduler import ejecutar_bucle_automatico, configurar_horarios_automaticos
from modules.database import mostrar_estadisticas_mensajes
from modules.scraper import scraping_hasta_no_haber_nuevos
from modules.sender import enviar_mensajes_individuales, generar_y_enviar_resumen_diario
from modules.utils import verificar_dependencias, cargar_configuracion
from modules.config import DEBUG


def mostrar_ayuda():
    print("""
WhatsApp LLM Bot - Sistema de Agregación Inteligente

USO:
  python whatsapp_bot.py [comando]

COMANDOS DISPONIBLES:
  --scraper     Ejecuta el scraping inmediatamente
  --send        Envía mensajes individuales
  --resumen     Envía el resumen diario consolidado
  --stats       Muestra estadísticas del día
  --auto        Ejecuta el bot en modo automático continuo
  --help        Muestra esta ayuda
""")


def main():
    cargar_configuracion()

    if not verificar_dependencias():
        print("Faltan dependencias requeridas. Revisa la configuración antes de continuar.")
        exit(1)

    parser = argparse.ArgumentParser(description="WhatsApp LLM Bot")
    parser.add_argument("--scraper", action="store_true", help="Ejecutar scraping")
    parser.add_argument("--send", action="store_true", help="Enviar mensajes individuales")
    parser.add_argument("--resumen", action="store_true", help="Enviar resumen diario")
    parser.add_argument("--stats", action="store_true", help="Mostrar estadísticas")
    parser.add_argument("--auto", action="store_true", help="Modo automático")

    args = parser.parse_args()

    if not any(vars(args).values()):
        mostrar_ayuda()
        return

    try:
        if args.scraper:
            print("[MAIN] Ejecutando scraping...")
            scraping_hasta_no_haber_nuevos()
        elif args.send:
            print("[MAIN] Enviando mensajes individuales...")
            enviar_mensajes_individuales()
        elif args.resumen:
            print("[MAIN] Enviando resumen diario...")
            generar_y_enviar_resumen_diario()
        elif args.stats:
            mostrar_estadisticas_mensajes()
        elif args.auto:
            print("[MAIN] Iniciando modo automático...")
            configurar_horarios_automaticos()
            ejecutar_bucle_automatico()
    except KeyboardInterrupt:
        print("\n[MAIN] Ejecución interrumpida por el usuario.")
    except Exception as e:
        print(f"[MAIN] Error inesperado: {e}")
        if DEBUG:
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
