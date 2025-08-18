import logging
import os
import django
from django.db import transaction
from asgiref.sync import sync_to_async
from crawler.models import Medicine, Generic, Manufacturer, DosageForm, Indication, DrugClass
from medexbot.items import MedItem, GenericItem, ManufacturerItem, DosageFormItem, IndicationItem, DrugClassItem

# Ensure Django is set up
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

logger = logging.getLogger(__name__)

class MedexbotPipeline:
    """Pipeline to save scraped items to database, avoiding duplicates."""

    def __init__(self):
        logger.info("🔧 MedexbotPipeline initialized!")
        logger.info(f"🔧 Pipeline settings: {self.__class__.__name__}")

    def process_item(self, item, spider):
        """Route items to appropriate handlers based on type."""
        logger.info(f"🔧 Processing item: {type(item).__name__} - {item}")
        
        handlers = {
            MedItem: self._save_medicine,
            GenericItem: self._save_generic,
            ManufacturerItem: self._save_manufacturer,
            DosageFormItem: self._save_dosage_form,
            IndicationItem: self._save_indication,
            DrugClassItem: self._save_drug_class,
        }

        handler = handlers.get(type(item))
        if handler:
            logger.info(f"🔧 Using handler: {handler.__name__}")
            return handler(item, spider)
        else:
            logger.warning(f"🔧 No handler found for item type: {type(item)}")
        return item

    def _save_if_not_exists(self, model, lookup_field, item, spider):
        """Generic method to save item if it doesn't already exist."""
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        from django.db import connection
        
        def _sync_save():
            """Synchronous database operation in separate thread."""
            try:
                with transaction.atomic():
                    existing = model.objects.get(**{lookup_field: item[lookup_field]})
                    logging.info(f"{model.__name__} with {lookup_field}={item[lookup_field]} already exists")
                    return existing
            except model.DoesNotExist:
                try:
                    item.save()
                    logging.info(f"Saved new {model.__name__} with {lookup_field}={item[lookup_field]}")
                    return item
                except Exception as e:
                    logging.error(f"Failed to save {model.__name__}: {e}")
                    return None
            except Exception as e:
                logging.error(f"Database error for {model.__name__}: {e}")
                return None
        
        # Run database operation in separate thread to avoid async context issues
        try:
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                future = executor.submit(_sync_save)
                result = future.result(timeout=10)  # 10 second timeout
                return result
        except Exception as e:
            logging.error(f"Thread execution error: {e}")
            return item

    def _save_medicine(self, item, spider):
        return self._save_if_not_exists(Medicine, "brand_id", item, spider)

    def _save_generic(self, item, spider):
        return self._save_if_not_exists(Generic, "generic_id", item, spider)

    def _save_manufacturer(self, item, spider):
        return self._save_if_not_exists(Manufacturer, "manufacturer_id", item, spider)

    def _save_dosage_form(self, item, spider):
        return self._save_if_not_exists(DosageForm, "dosage_form_id", item, spider)

    def _save_indication(self, item, spider):
        return self._save_if_not_exists(Indication, "indication_id", item, spider)

    def _save_drug_class(self, item, spider):
        return self._save_if_not_exists(DrugClass, "drug_class_id", item, spider)
