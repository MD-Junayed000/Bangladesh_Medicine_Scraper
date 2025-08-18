import logging
import os
import django
from django.db import transaction
from asgiref.sync import sync_to_async
from crawler.models import Medicine, Generic, Manufacturer, DosageForm, Indication, DrugClass
from medexbot.items import MedItem, GenericItem, ManufacturerItem, DosageFormItem, IndicationItem, DrugClassItem
from pathlib import Path

# Ensure Django is set up
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

logger = logging.getLogger(__name__)

class MedexbotPipeline:
    """Pipeline to save scraped items to database, avoiding duplicates."""

    def __init__(self):
        logger.info("🔧 MedexbotPipeline initialized!")
        logger.info(f"🔧 Pipeline settings: {self.__class__.__name__}")
        # Lazy caches for FK mapping files
        self._brand_to_generic = None
        self._brand_to_manufacturer = None
        self._generic_map_mtime = None
        self._manufacturer_map_mtime = None

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

    # ---------- Helpers for FK mapping ----------
    def _read_mapping_file(self, filename: str) -> dict:
        try:
            mapping_path = Path(filename)
            if not mapping_path.exists():
                return {}
            brand_to_fk = {}
            with mapping_path.open("r", encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split(",")
                    if len(parts) >= 2:
                        brand_id, fk_id = parts[0].strip(), parts[1].strip()
                        if brand_id and fk_id:
                            brand_to_fk[brand_id] = fk_id
            return brand_to_fk
        except Exception as exc:
            logging.error(f"Failed reading mapping file {filename}: {exc}")
            return {}

    def _refresh_fk_caches_if_needed(self):
        generic_path = Path("generic_id.txt")
        manf_path = Path("manufacturer_id.txt")
        # Refresh generic map
        try:
            mtime = generic_path.stat().st_mtime if generic_path.exists() else None
            if mtime and mtime != self._generic_map_mtime:
                self._brand_to_generic = self._read_mapping_file(str(generic_path))
                self._generic_map_mtime = mtime
        except Exception:
            self._brand_to_generic = self._brand_to_generic or {}
        # Refresh manufacturer map
        try:
            mtime = manf_path.stat().st_mtime if manf_path.exists() else None
            if mtime and mtime != self._manufacturer_map_mtime:
                self._brand_to_manufacturer = self._read_mapping_file(str(manf_path))
                self._manufacturer_map_mtime = mtime
        except Exception:
            self._brand_to_manufacturer = self._brand_to_manufacturer or {}

    def _attach_foreign_keys(self, item):
        """Populate Generic and Manufacturer on MedItem if missing using mapping files."""
        try:
            self._refresh_fk_caches_if_needed()
            brand_id = str(item.get("brand_id", "")).strip()
            if not brand_id:
                return item

            # Manufacturer
            if not item.get("manufacturer") and self._brand_to_manufacturer:
                manf_id = self._brand_to_manufacturer.get(brand_id)
                if manf_id:
                    try:
                        manf = Manufacturer.objects.filter(manufacturer_id=manf_id).first()
                        if manf:
                            item["manufacturer"] = manf
                    except Exception as exc:
                        logging.warning(f"Manufacturer lookup failed for {manf_id}: {exc}")

            # Generic
            if not item.get("generic") and self._brand_to_generic:
                generic_id = self._brand_to_generic.get(brand_id)
                if generic_id:
                    try:
                        gen = Generic.objects.filter(generic_id=generic_id).first()
                        if not gen:
                            # Create a lightweight placeholder so relation is not empty.
                            # This will be enriched/updated when the real GenericItem arrives.
                            placeholder_name = f"Generic {generic_id}"
                            gen = Generic.objects.create(
                                generic_id=generic_id,
                                generic_name=placeholder_name,
                                slug=f"generic-{generic_id}",
                            )
                        item["generic"] = gen
                    except Exception as exc:
                        logging.warning(f"Generic attach/create failed for {generic_id}: {exc}")
        except Exception as exc:
            logging.error(f"Failed to attach foreign keys: {exc}")
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
                    # Attach FK relations before checking/saving
                    try:
                        if isinstance(item, MedItem):
                            self._attach_foreign_keys(item)
                    except Exception:
                        pass
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
        # Attach drug_class and indication from hints if present
        try:
            dc_id = item.get('drug_class_id_hint')
            if dc_id and not item.get('drug_class'):
                try:
                    dc = DrugClass.objects.filter(drug_class_id=dc_id).first()
                    if dc:
                        item['drug_class'] = dc
                except Exception as exc:
                    logging.warning(f"DrugClass lookup failed for {dc_id}: {exc}")
            ind_id = item.get('indication_id_hint')
            if ind_id and not item.get('indication'):
                try:
                    ind = Indication.objects.filter(indication_id=ind_id).first()
                    if ind:
                        item['indication'] = ind
                except Exception as exc:
                    logging.warning(f"Indication lookup failed for {ind_id}: {exc}")
        except Exception:
            pass
        return self._save_if_not_exists(Generic, "generic_id", item, spider)

    def _save_manufacturer(self, item, spider):
        return self._save_if_not_exists(Manufacturer, "manufacturer_id", item, spider)

    def _save_dosage_form(self, item, spider):
        return self._save_if_not_exists(DosageForm, "dosage_form_id", item, spider)

    def _save_indication(self, item, spider):
        return self._save_if_not_exists(Indication, "indication_id", item, spider)

    def _save_drug_class(self, item, spider):
        return self._save_if_not_exists(DrugClass, "drug_class_id", item, spider)
