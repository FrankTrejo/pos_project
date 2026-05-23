from django.db import models

class Configuracion(models.Model):
    # --- 1. IDENTIDAD DEL NEGOCIO (Para el Ticket) ---
    nombre_empresa = models.CharField(max_length=100, default="Di Catia Pizzas")
    rif = models.CharField(max_length=20, default="J-00000000-0", verbose_name="RIF / ID Fiscal")
    direccion = models.TextField(blank=True, default="Caracas, Venezuela")
    telefono = models.CharField(max_length=50, blank=True)
    mensaje_ticket = models.CharField(max_length=200, default="¡Gracias por su compra!", help_text="Mensaje al final de la factura")
    logo = models.ImageField(upload_to='logos/', blank=True, null=True)

    # --- 2. MONEDA E IMPUESTOS ---
    tasa_dolar = models.DecimalField(max_digits=10, decimal_places=2, default=40.00, verbose_name="Tasa BCV ($)")
    
    # --- 3. AUTOMATIZACIÓN Y PROCESOS ---
    usar_scraping_bcv = models.BooleanField(default=True, verbose_name="¿Actualizar Tasa BCV automáticamente?", help_text="Si se desactiva, el sistema utilizará la tasa manual ingresada arriba.")
    enviar_alerta_stock_correo = models.BooleanField(default=False, verbose_name="¿Enviar alerta de stock por correo?")
    correo_destino_alertas = models.EmailField(blank=True, null=True, verbose_name="Correo para alertas", help_text="Correo donde llegará el PDF de insumos agotados.")
    codigo_producto_automatico = models.BooleanField(
        default=True,
        verbose_name="¿Código de producto automático?",
        help_text="Si está marcado, se generará un código autoincrementable. Si está desmarcado, podrás ingresarlo manualmente."
    )

    # --- 4. CONFIGURACIÓN DE IMPRESIÓN (NUEVO) ---
    impresora_ticket = models.CharField(max_length=100, blank=True, default="", verbose_name="Nombre Impresora (Referencia)", help_text="Nombre de la impresora predeterminada en el sistema operativo")
    ancho_papel = models.IntegerField(default=80, verbose_name="Ancho Papel (mm)", help_text="Estándar: 80mm o 58mm")
    auto_imprimir = models.BooleanField(default=True, verbose_name="¿Impresión Automática?", help_text="Si se marca, el sistema intentará imprimir sin preguntar al cerrar la venta.")

    # --- 5. CONFIGURACIÓN DE EMPAQUES (NUEVO) ---
    caja_individual = models.ForeignKey('inventory.Insumo', related_name='config_caja_ind', on_delete=models.SET_NULL, null=True, blank=True, limit_choices_to={'es_insumo_compuesto': False}, verbose_name="Empaque Individual")
    caja_mediana = models.ForeignKey('inventory.Insumo', related_name='config_caja_med', on_delete=models.SET_NULL, null=True, blank=True, limit_choices_to={'es_insumo_compuesto': False}, verbose_name="Empaque Mediano")
    caja_familiar = models.ForeignKey('inventory.Insumo', related_name='config_caja_fam', on_delete=models.SET_NULL, null=True, blank=True, limit_choices_to={'es_insumo_compuesto': False}, verbose_name="Empaque Familiar")
    
    def __str__(self):
        return "Configuración General"

    class Meta:
        verbose_name = "Configuración"
        verbose_name_plural = "Configuración"

    # --- MÉTODO MÁGICO SINGLETON ---
    # Esto asegura que siempre llamemos a la misma configuración (ID=1)
    @classmethod
    def get_solo(cls):
        obj, created = cls.objects.get_or_create(id=1)
        return obj

    # Evitar crear más de un registro
    def save(self, *args, **kwargs):
        self.pk = 1
        super(Configuracion, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass # No permitir borrar la configuración