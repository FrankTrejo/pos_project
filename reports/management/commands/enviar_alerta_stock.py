from django.core.management.base import BaseCommand
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from django.db.models import F, ExpressionWrapper, DecimalField
from inventory.models import Insumo
import datetime
from io import BytesIO
from xhtml2pdf import pisa

class Command(BaseCommand):
    help = 'Genera PDF de alertas de stock y lo envía por correo'

    def handle(self, *args, **options):
        self.stdout.write("Analizando inventario...")

        # 1. Obtener datos (Calculando déficit igual que en la vista)
        insumos_criticos = Insumo.objects.filter(
            stock_actual__lte=F('stock_minimo')
        ).annotate(
            deficit=ExpressionWrapper(
                F('stock_minimo') - F('stock_actual'),
                output_field=DecimalField()
            )
        ).order_by('stock_actual')

        if insumos_criticos.exists():
            fecha_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
            
            # 2. Renderizar el HTML con los datos
            context = {
                'insumos': insumos_criticos,
                'fecha': fecha_str
            }
            html_string = render_to_string('reports/pdf_alerta.html', context)

            # 3. Convertir HTML a PDF en memoria (BytesIO)
            # Esto evita tener que guardar el archivo en el disco duro
            pdf_file = BytesIO()
            pisa_status = pisa.CreatePDF(html_string, dest=pdf_file)

            if pisa_status.err:
                self.stdout.write(self.style.ERROR('Error generando el PDF'))
                return

            # 4. Configurar el Correo con Adjunto
            subject = f'🚨 REPORTE PDF: Insumos Agotados ({fecha_str})'
            body = 'Adjunto encontrarás el reporte detallado de los insumos que requieren compra inmediata.'
            email_from = settings.EMAIL_HOST_USER
            recipient_list = ['frankdtg2004@hotmail.com'] # <--- REVISA TU CORREO AQUÍ

            email = EmailMessage(
                subject,
                body,
                email_from,
                recipient_list,
            )

            # Adjuntar el PDF desde la memoria
            # nombre_archivo, contenido, tipo_mime
            email.attach('Alerta_Stock.pdf', pdf_file.getvalue(), 'application/pdf')

            try:
                email.send()
                self.stdout.write(self.style.SUCCESS(f'✅ Correo con PDF enviado exitosamente ({insumos_criticos.count()} items).'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Error enviando correo: {e}'))
            
            # Cerrar el archivo en memoria
            pdf_file.close()

        else:
            self.stdout.write(self.style.SUCCESS('Inventario OK. No se generó reporte.'))