from django.core.management.base import BaseCommand
from django.db import transaction
from crawler.models import Medicine, Generic

# common names people use for the external MedEx generic id on Medicine
CANDIDATE_EXT_FIELDS = [
    "medex_generic_id",
    "generic_medex_id",
    "generic_external_id",
    "generic_source_id",
    "generic_ref_id",
    "gen_external_id",
    "gen_id",
    # NOTE: we do NOT blindly use "generic_id" because Django will also
    # create <fkname>_id for the FK to Generic. That would collide.
]

def find_fk_to_generic():
    for f in Medicine._meta.get_fields():
        if getattr(getattr(f, "remote_field", None), "model", None) is Generic:
            return f.name  # e.g., "generic"
    return None

def guess_external_field(medicine_fk_name):
    # Avoid picking the FK id column (e.g., "generic_id")
    fk_id_field = f"{medicine_fk_name}_id" if medicine_fk_name else None
    names = {f.name for f in Medicine._meta.get_fields()}
    for cand in CANDIDATE_EXT_FIELDS:
        if cand in names:
            return cand
    # last resort: if there *is* a "generic_id" field AND it is not the FK id
    if "generic_id" in names and "generic_id" != fk_id_field:
        return "generic_id"
    return None

class Command(BaseCommand):
    help = "Link Medicine.generic FK based on MedEx generic id stored on Medicine."

    def add_arguments(self, parser):
        parser.add_argument(
            "--external-field",
            dest="external_field",
            default=None,
            help="Field name on Medicine that stores the MedEx generic id "
                 "(e.g. medex_generic_id). If omitted, the command will try to guess.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be updated without writing to the database.",
        )

    def handle(self, *args, **opts):
        self.stdout.write("Mapping the generics with medicines")

        fk_name = find_fk_to_generic()
        if not fk_name:
            self.stderr.write(
                "❌ No ForeignKey from Medicine to Generic was found. "
                "Add one (e.g., `generic = models.ForeignKey(Generic, ...)`)."
            )
            return

        ext_field = opts["external_field"] or guess_external_field(fk_name)
        if not ext_field or not hasattr(Medicine, ext_field):
            self.stderr.write(
                "❌ Could not find which Medicine field contains the MedEx generic id.\n"
                f"   Pass it explicitly:  python manage.py med_generic_mapper --external-field FIELD_NAME\n"
                f"   Known candidates tried: {', '.join(CANDIDATE_EXT_FIELDS + ['generic_id'])}"
            )
            return

        fk_id_field = f"{fk_name}_id"

        # Build lookup: external MedEx generic id -> Generic PK
        gen_map = {g.generic_id: g.pk for g in Generic.objects.only("id", "generic_id")}
        if not gen_map:
            self.stderr.write("❌ No Generic rows found. Crawl/save generics first.")
            return

        qs = (Medicine.objects
              .exclude(**{ext_field: None})
              .only("id", ext_field, fk_id_field))
        total = qs.count()
        if total == 0:
            self.stdout.write("ℹ️ No medicines have a non-null external generic id.")
            return

        to_update, already_ok, missing = [], 0, 0
        for m in qs.iterator(chunk_size=1000):
            ext_val = getattr(m, ext_field)
            gen_pk = gen_map.get(ext_val)
            if gen_pk is None:
                missing += 1
                continue
            if getattr(m, fk_id_field) == gen_pk:
                already_ok += 1
                continue
            setattr(m, fk_id_field, gen_pk)
            to_update.append(m)

        self.stdout.write(
            f"Found {total} medicines with '{ext_field}'. "
            f"{already_ok} already linked, {missing} with unknown generic ids, "
            f"{len(to_update)} to update."
        )

        if not to_update:
            self.stdout.write(self.style.WARNING("Nothing to update."))
            return

        if opts["dry_run"]:
            self.stdout.write(self.style.WARNING("Dry run: no changes written."))
            return

        with transaction.atomic():
            Medicine.objects.bulk_update(to_update, [fk_id_field], batch_size=500)

        self.stdout.write(self.style.SUCCESS(f"✅ Updated {len(to_update)} medicines."))
