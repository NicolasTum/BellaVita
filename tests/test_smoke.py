from pathlib import Path

from app.config.settings import SETTINGS
from app.database.bootstrap import DEFAULT_ADMIN_USERNAME, ensure_default_admin
from app.database.schema import initialize_database
from app.services.customers import CustomerService, CustomerValidationError
from app.version import VERSION


def test_settings_are_centralized() -> None:
    assert SETTINGS.app_name == "Club de Compras"
    assert SETTINGS.version == VERSION
    assert SETTINGS.stickers_per_cycle == 6
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    assert f'version = "{VERSION}"' in pyproject


def test_database_initializes(tmp_path) -> None:
    db_path = tmp_path / "club_compras.db"
    initialize_database(db_path)
    assert db_path.exists()


def test_default_admin_is_created_once(tmp_path) -> None:
    db_path = tmp_path / "club_compras.db"
    initialize_database(db_path)

    assert ensure_default_admin(db_path) is True
    assert ensure_default_admin(db_path) is False

    import sqlite3

    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            "SELECT username, role, must_change_password FROM users"
        ).fetchone()

    assert row == (DEFAULT_ADMIN_USERNAME, "admin", 1)


def test_customer_service_creates_customer(tmp_path) -> None:
    db_path = tmp_path / "club_compras.db"
    initialize_database(db_path)
    service = CustomerService(db_path)

    customer = service.build_customer(
        first_name="Ana",
        last_name="Perez",
        phone="099123456",
        email="",
        notes="Cliente de prueba",
        marketing_consent=True,
    )
    result = service.create_customer(customer)

    assert result.customer_id == 1

    saved = service.get_customer(result.customer_id)
    assert saved is not None
    assert saved.full_name == "Ana Perez"
    assert saved.is_active is True
    assert saved.marketing_consent is True


def test_customer_requires_contact_method(tmp_path) -> None:
    db_path = tmp_path / "club_compras.db"
    initialize_database(db_path)
    service = CustomerService(db_path)

    try:
        service.build_customer(
            first_name="Ana",
            last_name="Perez",
            phone="",
            email="",
            notes="",
            marketing_consent=False,
        )
    except CustomerValidationError as exc:
        assert "teléfono o un correo" in str(exc)
    else:
        raise AssertionError("Expected CustomerValidationError")


def test_customer_search_update_and_deactivate(tmp_path) -> None:
    db_path = tmp_path / "club_compras.db"
    initialize_database(db_path)
    service = CustomerService(db_path)

    customer = service.build_customer(
        first_name="Lucia",
        last_name="Silva",
        phone="",
        email="lucia@example.com",
        notes="",
        marketing_consent=False,
    )
    customer_id = service.create_customer(customer).customer_id

    assert [item.id for item in service.search_customers("lucia")] == [customer_id]

    updated = service.build_customer(
        first_name="Lucia",
        last_name="Martinez",
        phone="091111111",
        email="lucia@example.com",
        notes="Actualizada",
        marketing_consent=True,
    )
    service.update_customer(customer_id, updated)
    service.set_customer_active(customer_id, False)

    saved = service.get_customer(customer_id)
    assert saved is not None
    assert saved.last_name == "Martinez"
    assert saved.phone == "091111111"
    assert saved.marketing_consent is True
    assert saved.is_active is False


def test_customer_consent_can_be_saved_as_unchecked(tmp_path) -> None:
    db_path = tmp_path / "club_compras.db"
    initialize_database(db_path)
    service = CustomerService(db_path)

    customer_id = service.create_customer(
        service.build_customer(
            first_name="No",
            last_name="Promo",
            phone="099000111",
            email="",
            notes="",
            marketing_consent=False,
        )
    ).customer_id

    saved = service.get_customer(customer_id)

    assert saved is not None
    assert saved.marketing_consent is False


def test_windows_runtime_paths_are_under_localappdata(tmp_path, monkeypatch) -> None:
    from app.utils import paths

    monkeypatch.setattr(paths.sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "LocalAppData"))

    assert paths.database_path() == tmp_path / "LocalAppData" / "ClubCompras" / "data" / "club_compras.db"
    assert paths.log_dir() == tmp_path / "LocalAppData" / "ClubCompras" / "logs"
    assert paths.backup_dir() == tmp_path / "LocalAppData" / "ClubCompras" / "backups"
    assert paths.export_dir() == tmp_path / "LocalAppData" / "ClubCompras" / "exports"
    assert paths.config_dir() == tmp_path / "LocalAppData" / "ClubCompras" / "config"

    paths.ensure_runtime_dirs()

    assert paths.database_path().parent.is_dir()
    assert paths.log_dir().is_dir()
    assert paths.backup_dir().is_dir()
    assert paths.export_dir().is_dir()
    assert paths.config_dir().is_dir()


def test_windows_build_files_do_not_include_development_database() -> None:
    spec = Path("club_compras_windows.spec").read_text(encoding="utf-8")
    build_script = Path("scripts/build_windows.ps1").read_text(encoding="utf-8")
    installer = Path("installer/windows/ClubDeCompras.iss").read_text(encoding="utf-8")
    workflow = Path(".github/workflows/build-windows-installer.yml").read_text(encoding="utf-8")

    assert '("assets", "assets")' in spec
    assert 'name="ClubDeCompras"' in spec
    assert "club_compras.db" not in spec
    assert "data" in spec
    assert "dist\\ClubDeCompras" in build_script
    assert "ClubDeCompras.exe" in build_script
    assert "BellaVita_ClubDeCompras_Setup_$Version.exe" in build_script
    assert "club_compras.db" not in installer
    assert 'Source: "..\\..\\dist\\ClubDeCompras\\*"' in installer
    assert '#define MyAppExeName "ClubDeCompras.exe"' in installer
    assert "BellaVita-ClubDeCompras-Windows-Installer" in workflow
    assert "Build Windows Installer" in workflow
    assert "dist/installer/BellaVita_ClubDeCompras_Setup_${{ steps.app_version.outputs.version }}.exe" in workflow
    assert "/Users/" not in installer


def test_windows_installer_configuration_preserves_user_data() -> None:
    installer = Path("installer/windows/ClubDeCompras.iss").read_text(encoding="utf-8")
    notice = Path("installer/windows/datos_conservados.txt").read_text(encoding="utf-8")

    assert '#define MyAppDirName "Bella Vita\\Club de Compras"' in installer
    assert "DefaultDirName={autopf}\\{#MyAppDirName}" in installer
    assert "ArchitecturesAllowed=x64" in installer
    assert "ArchitecturesInstallIn64BitMode=x64" in installer
    assert "CloseApplications=yes" in installer
    assert "Name: \"{autoprograms}\\{#MyAppName}\"" in installer
    assert "Name: \"{autodesktop}\\{#MyAppName}\"" in installer
    assert "[UninstallDelete]" in installer
    assert "%LOCALAPPDATA%\\ClubCompras" in notice


def test_packaging_sources_do_not_use_personal_absolute_paths() -> None:
    checked_paths = [
        Path("app"),
        Path("scripts"),
        Path("installer"),
        Path(".github/workflows"),
        Path("club_compras_windows.spec"),
        Path("club_compras_macos.spec"),
    ]
    forbidden = ["/Users/nicolastumaian", "/Users/", "/Applications/"]
    for path in checked_paths:
        files = [path] if path.is_file() else [item for item in path.rglob("*") if item.is_file()]
        for file_path in files:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            for value in forbidden:
                assert value not in text, f"{value} found in {file_path}"
