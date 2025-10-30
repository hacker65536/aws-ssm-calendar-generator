"""Command line interface module."""

import click
import os
from datetime import datetime, date
from typing import Optional
from contextlib import nullcontext

from .aws_client import SSMChangeCalendarClient
from .ics_generator import ICSGenerator
from .datetime_handler import DateTimeHandler
from .config import Config
from .japanese_holidays import JapaneseHolidays
from .change_calendar_manager import ChangeCalendarManager
from .calendar_analyzer import ICSAnalyzer
from .error_handler import (
    BaseApplicationError, handle_error, ErrorCategory, ErrorSeverity,
    AWSError, ConfigurationError, FileSystemError, ValidationError
)
from .security import (
    validate_calendar_name_input, validate_file_path_input, validate_date_input
)
from .logging_config import (
    setup_logging, LogLevel, LogFormat, log_performance, 
    log_function_call, set_debug_mode, cleanup_logging
)
import json


@click.group()
@click.option('--config', '-c', help='Configuration file path')
@click.option('--profile', '-p', help='AWS profile name')
@click.option('--region', '-r', help='AWS region')
@click.option('--debug', is_flag=True, help='Enable debug mode with verbose logging')
@click.option('--log-level', type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']), 
              default='WARNING', help='Set logging level')
@click.option('--log-format', type=click.Choice(['simple', 'detailed', 'json', 'structured']), 
              default='simple', help='Set log format')
@click.option('--enable-monitoring', is_flag=True, help='Enable performance and system monitoring')
@click.pass_context
def cli(ctx, config: Optional[str], profile: Optional[str], region: Optional[str], 
        debug: bool, log_level: str, log_format: str, enable_monitoring: bool):
    """AWS SSM Change Calendar to ICS converter with Japanese holidays support.
    
    Examples:
      python main.py holidays --year 2024 --output holidays.ics
      python main.py export MyCalendar --include-holidays -o calendar.ics
      python main.py check-holiday --date 2024-11-03
    """
    ctx.ensure_object(dict)
    
    try:
        # Setup logging and monitoring
        log_level_enum = getattr(LogLevel, log_level)
        log_format_enum = getattr(LogFormat, log_format.upper())
        
        logging_manager = setup_logging(
            log_level=log_level_enum,
            log_format=log_format_enum,
            enable_performance_monitoring=enable_monitoring,
            enable_system_monitoring=enable_monitoring,
            debug_mode=debug
        )
        
        ctx.obj['logging_manager'] = logging_manager
        
        # Load configuration
        ctx.obj['config'] = Config(config)
        
        # Override config with CLI options
        if profile:
            ctx.obj['config'].set('aws.profile', profile)
        if region:
            ctx.obj['config'].set('aws.region', region)
            
    except Exception as e:
        error = ConfigurationError(
            f"Failed to initialize application: {e}",
            operation="cli_initialization"
        )
        handle_error(error)
        click.echo(f"Error: {error.get_user_message()}", err=True)
        raise click.Abort()


@cli.command()
@click.argument('calendar_name')
@click.option('--output', '-o', help='Output file path')
@click.option('--timezone', '-t', default='UTC', help='Output timezone')
@click.option('--include-holidays', is_flag=True, help='Include Japanese holidays')
@click.option('--holidays-year', type=int, help='Year for Japanese holidays (default: current year)')
@click.pass_context
@log_performance("export_calendar")
@log_function_call(log_args=True)
def export(ctx, calendar_name: str, output: Optional[str], timezone: str, include_holidays: bool, holidays_year: Optional[int]):
    """Export change calendar to ICS file."""
    config = ctx.obj['config']
    logging_manager = ctx.obj['logging_manager']
    
    with logging_manager.monitor_operation("export_calendar", {
        "calendar_name": calendar_name,
        "include_holidays": include_holidays,
        "timezone": timezone
    }):
        try:
            # Validate inputs
            validated_calendar_name = validate_calendar_name_input(calendar_name)
            
            if output:
                validated_output = validate_file_path_input(output, allow_create=True)
                output = str(validated_output)
            
            # Initialize components
            aws_config = config.get_aws_config()
            ssm_client = SSMChangeCalendarClient(
                region_name=aws_config.get('region', 'us-east-1'),
                profile_name=aws_config.get('profile')
            )
            
            ics_generator = ICSGenerator(include_japanese_holidays=include_holidays)
            dt_handler = DateTimeHandler(timezone)
            
            # Get calendar data
            click.echo(f"Fetching calendar: {validated_calendar_name}")
            calendar_data = ssm_client.get_change_calendar(validated_calendar_name)
            
            # Parse and add events
            events = ics_generator.parse_ssm_calendar_data(calendar_data)
            
            for event in events:
                if event.get('start') and event.get('end'):
                    start_dt = dt_handler.parse_aws_datetime(event['start'])
                    end_dt = dt_handler.parse_aws_datetime(event['end'])
                    
                    ics_generator.add_change_window(
                        title=event.get('title', 'Change Window'),
                        start_time=start_dt,
                        end_time=end_dt,
                        description=event.get('description', ''),
                        calendar_name=validated_calendar_name
                    )
            
            # Add Japanese holidays if requested
            if include_holidays:
                year = holidays_year or datetime.now().year
                click.echo(f"Adding Japanese holidays for year {year}")
                ics_generator.add_japanese_holidays_for_year(year)
            
            # Generate output filename if not provided
            if not output:
                output_config = config.get_output_config()
                output_dir = output_config.get('directory', './output')
                os.makedirs(output_dir, exist_ok=True)
                
                date_str = datetime.now().strftime('%Y%m%d')
                filename = output_config.get('filename_template', '{calendar_name}_{date}.ics')
                output_filename = filename.format(calendar_name=validated_calendar_name, date=date_str)
                output_path = os.path.join(output_dir, output_filename)
                validated_output_path = validate_file_path_input(output_path, allow_create=True)
                output = str(validated_output_path)
            
            # Save ICS file
            ics_generator.save_to_file(output)
            click.echo(f"Calendar exported to: {output}")
            
        except ValidationError as e:
            handle_error(e, {"operation": "export_calendar", "calendar_name": calendar_name})
            click.echo(f"Validation Error: {e.get_user_message()}", err=True)
            raise click.Abort()
        except BaseApplicationError as e:
            handle_error(e, {"operation": "export_calendar", "calendar_name": calendar_name})
            click.echo(f"Error: {e.get_user_message()}", err=True)
            raise click.Abort()
        except Exception as e:
            error = AWSError(
                f"Failed to export calendar: {e}",
                operation="export_calendar",
                service="ssm"
            )
            handle_error(error, {"calendar_name": calendar_name})
            click.echo(f"Error: {error.get_user_message()}", err=True)
            raise click.Abort()


@cli.command()
@click.pass_context
def list_calendars(ctx):
    """List available change calendars."""
    config = ctx.obj['config']
    
    try:
        aws_config = config.get_aws_config()
        ssm_client = SSMChangeCalendarClient(
            region_name=aws_config.get('region', 'us-east-1'),
            profile_name=aws_config.get('profile')
        )
        
        calendars = ssm_client.list_change_calendars()
        
        if calendars:
            click.echo("Available Change Calendars:")
            for calendar in calendars:
                name = calendar.get('Name', 'Unknown')
                click.echo(f"  - {name}")
        else:
            click.echo("No change calendars found.")
            
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument('calendar_name')
@click.pass_context
def status(ctx, calendar_name: str):
    """Check change calendar status."""
    config = ctx.obj['config']
    
    try:
        aws_config = config.get_aws_config()
        ssm_client = SSMChangeCalendarClient(
            region_name=aws_config.get('region', 'us-east-1'),
            profile_name=aws_config.get('profile')
        )
        
        state = ssm_client.get_calendar_state(calendar_name)
        click.echo(f"Calendar '{calendar_name}' is currently: {state}")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option('--year', '-y', type=int, help='Year to show holidays for (default: current year onwards)')
@click.option('--output', '-o', help='Output ICS file for holidays only')
@click.pass_context
def holidays(ctx, year: Optional[int], output: Optional[str]):
    """Show or export Japanese holidays."""
    try:
        jp_holidays = JapaneseHolidays()
        
        if year:
            # 特定年が指定された場合はその年のみ（日曜祝日フィルタリング適用）
            ics_generator = ICSGenerator()
            start_date = date(year, 1, 1)
            end_date = date(year, 12, 31)
            all_holidays = jp_holidays.get_holidays_in_range(start_date, end_date)
            
            # 日曜祝日フィルタリングを適用
            filtered_holidays, sunday_holidays = ics_generator.filter_sunday_holidays(all_holidays)
            
            if not filtered_holidays:
                click.echo(f"No holidays found for year {year}")
                return
            
            click.echo(f"Japanese holidays for {year} - excluding Sunday holidays:")
            for holiday_date, holiday_name in filtered_holidays:
                click.echo(f"  {holiday_date.strftime('%Y-%m-%d')} ({holiday_date.strftime('%a')}) - {holiday_name}")
            
            if sunday_holidays:
                click.echo(f"\nExcluded Sunday holidays: {len(sunday_holidays)} events")
                for holiday_date, holiday_name in sunday_holidays:
                    click.echo(f"  {holiday_date.strftime('%Y-%m-%d')} (Sun) - {holiday_name} [excluded]")
            
            # Export to ICS if requested
            if output:
                ics_generator.add_japanese_holidays_for_year(year)
                ics_generator.save_to_file(output)
                click.echo(f"Holidays exported to: {output}")
        else:
            # 年指定がない場合は当年以降の全データ（日曜祝日フィルタリング適用）
            current_year = datetime.now().year
            stats = jp_holidays.get_stats()
            
            # ICSGeneratorを使用して日曜祝日フィルタリングを適用
            ics_generator = ICSGenerator()
            filtered_holidays = ics_generator.convert_current_year_onwards_holidays()
            
            if not filtered_holidays:
                click.echo(f"No holidays found from {current_year} onwards")
                return
            
            click.echo(f"Japanese holidays from {current_year} onwards ({current_year}-{stats['max_year']}) - excluding Sunday holidays:")
            
            # 年別にグループ化して表示
            holidays_by_year = {}
            for holiday_date, holiday_name in filtered_holidays:
                year_key = holiday_date.year
                if year_key not in holidays_by_year:
                    holidays_by_year[year_key] = []
                holidays_by_year[year_key].append((holiday_date, holiday_name))
            
            for year_key in sorted(holidays_by_year.keys()):
                click.echo(f"\n  {year_key}年:")
                for holiday_date, holiday_name in holidays_by_year[year_key]:
                    click.echo(f"    {holiday_date.strftime('%Y-%m-%d')} ({holiday_date.strftime('%a')}) - {holiday_name}")
            
            click.echo(f"\nTotal: {len(filtered_holidays)} holidays across {len(holidays_by_year)} years")
            
            # Export to ICS if requested
            if output:
                # 既にフィルタリング済みのデータを使用してICS生成
                ics_generator.convert_holidays_to_events()
                ics_generator.save_to_file(output)
                click.echo(f"Holidays exported to: {output}")
            
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.pass_context
def refresh_holidays(ctx):
    """Refresh Japanese holidays data from Cabinet Office."""
    try:
        click.echo("Refreshing Japanese holidays data...")
        jp_holidays = JapaneseHolidays()
        jp_holidays.refresh_data()
        
        stats = jp_holidays.get_stats()
        click.echo(f"Successfully refreshed holidays data:")
        click.echo(f"  Total holidays: {stats['total']}")
        click.echo(f"  Years covered: {stats['years']} ({stats['min_year']}-{stats['max_year']})")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option('--date', '-d', help='Date to check (YYYY-MM-DD format, default: today)')
@click.pass_context
def check_holiday(ctx, date: Optional[str]):
    """Check if a specific date is a Japanese holiday."""
    try:
        jp_holidays = JapaneseHolidays()
        
        if date:
            check_date = datetime.strptime(date, '%Y-%m-%d').date()
        else:
            check_date = datetime.now().date()
        
        if jp_holidays.is_holiday(check_date):
            holiday_name = jp_holidays.get_holiday_name(check_date)
            click.echo(f"{check_date.strftime('%Y-%m-%d')} is a Japanese holiday: {holiday_name}")
        else:
            click.echo(f"{check_date.strftime('%Y-%m-%d')} is not a Japanese holiday")
            
            # Show next holiday
            next_holiday = jp_holidays.get_next_holiday(check_date)
            if next_holiday:
                next_date, next_name = next_holiday
                days_until = (next_date - check_date).days
                click.echo(f"Next holiday: {next_date.strftime('%Y-%m-%d')} ({next_name}) in {days_until} days")
        
    except ValueError:
        click.echo("Error: Invalid date format. Use YYYY-MM-DD format.", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument('calendar_name')
@click.option('--year', '-y', type=int, help='Year for holidays (default: current year)')
@click.option('--description', '-d', help='Description for the calendar')
@click.pass_context
def create_calendar(ctx, calendar_name: str, year: Optional[int], description: Optional[str]):
    """Create a new Change Calendar with Japanese holidays."""
    config = ctx.obj['config']
    
    try:
        target_year = year or datetime.now().year
        
        # Initialize Change Calendar Manager
        aws_config = config.get_aws_config()
        manager = ChangeCalendarManager(
            region_name=aws_config.get('region', 'ap-northeast-1'),
            profile_name=aws_config.get('profile')
        )
        
        click.echo(f"Creating Change Calendar: {calendar_name}")
        click.echo(f"Year range: {target_year}-{target_year + 1}")
        
        # Create the calendar
        result = manager.create_japanese_holiday_calendar(
            calendar_name=calendar_name,
            year=target_year,
            description=description or f"Japanese holidays for {target_year}-{target_year + 1}"
        )
        
        click.echo(f"✅ Change Calendar created successfully!")
        click.echo(f"  Name: {result['calendar_name']}")
        click.echo(f"  Status: {result['status']}")
        click.echo(f"  Version: {result['version']}")
        click.echo(f"  Holiday count: {result['holiday_count']}")
        click.echo(f"  Year range: {result['year_range']}")
        click.echo(f"  ICS size: {result['ics_size']} characters")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument('calendar_name')
@click.option('--year', '-y', type=int, help='Year for holidays (default: current year)')
@click.option('--preserve', is_flag=True, help='Preserve existing events (not yet implemented)')
@click.pass_context
def update_calendar(ctx, calendar_name: str, year: Optional[int], preserve: bool):
    """Update an existing Change Calendar with Japanese holidays."""
    config = ctx.obj['config']
    
    try:
        target_year = year or datetime.now().year
        
        # Initialize Change Calendar Manager
        aws_config = config.get_aws_config()
        manager = ChangeCalendarManager(
            region_name=aws_config.get('region', 'ap-northeast-1'),
            profile_name=aws_config.get('profile')
        )
        
        click.echo(f"Updating Change Calendar: {calendar_name}")
        click.echo(f"Year range: {target_year}-{target_year + 1}")
        
        if preserve:
            click.echo("⚠️  Preserve existing events is not yet implemented")
        
        # Update the calendar
        result = manager.update_existing_calendar_with_holidays(
            calendar_name=calendar_name,
            year=target_year,
            preserve_existing=preserve
        )
        
        click.echo(f"✅ Change Calendar updated successfully!")
        click.echo(f"  Name: {result['calendar_name']}")
        click.echo(f"  Status: {result['status']}")
        click.echo(f"  Version: {result['version']}")
        click.echo(f"  Holiday count: {result['holiday_count']}")
        click.echo(f"  Year range: {result['year_range']}")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.pass_context
def list_calendars(ctx):
    """List all Change Calendars."""
    config = ctx.obj['config']
    
    try:
        # Initialize Change Calendar Manager
        aws_config = config.get_aws_config()
        manager = ChangeCalendarManager(
            region_name=aws_config.get('region', 'ap-northeast-1'),
            profile_name=aws_config.get('profile')
        )
        
        calendars = manager.list_change_calendars()
        
        if calendars:
            click.echo("Available Change Calendars:")
            for calendar in calendars:
                click.echo(f"  📅 {calendar['name']}")
                click.echo(f"    State: {calendar['current_state']}")
                click.echo(f"    Version: {calendar['version']}")
                click.echo(f"    Format: {calendar['format']}")
                if 'created_date' in calendar:
                    click.echo(f"    Created: {calendar['created_date']}")
                if 'error' in calendar:
                    click.echo(f"    ⚠️  Error: {calendar['error']}")
                click.echo()
        else:
            click.echo("No Change Calendars found.")
            
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument('calendar_name')
@click.pass_context
def calendar_info(ctx, calendar_name: str):
    """Get detailed information about a Change Calendar."""
    config = ctx.obj['config']
    
    try:
        # Initialize Change Calendar Manager
        aws_config = config.get_aws_config()
        manager = ChangeCalendarManager(
            region_name=aws_config.get('region', 'ap-northeast-1'),
            profile_name=aws_config.get('profile')
        )
        
        info = manager.get_calendar_info(calendar_name)
        
        click.echo(f"Change Calendar Information: {calendar_name}")
        click.echo(f"  Status: {info['status']}")
        click.echo(f"  Current State: {info['current_state']}")
        click.echo(f"  Version: {info['version']}")
        click.echo(f"  Format: {info['format']}")
        click.echo(f"  Content Size: {info['content_size']} characters")
        if info.get('created_date'):
            click.echo(f"  Created: {info['created_date']}")
        if info.get('modified_date'):
            click.echo(f"  Modified: {info['modified_date']}")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument('calendar_name')
@click.confirmation_option(prompt='Are you sure you want to delete this calendar?')
@click.pass_context
def delete_calendar(ctx, calendar_name: str):
    """Delete a Change Calendar."""
    config = ctx.obj['config']
    
    try:
        # Initialize Change Calendar Manager
        aws_config = config.get_aws_config()
        manager = ChangeCalendarManager(
            region_name=aws_config.get('region', 'ap-northeast-1'),
            profile_name=aws_config.get('profile')
        )
        
        result = manager.delete_calendar(calendar_name)
        
        click.echo(f"✅ Change Calendar deleted successfully!")
        click.echo(f"  Name: {result['calendar_name']}")
        click.echo(f"  Deleted: {result['deleted_date']}")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument('calendar_name')
@click.option('--output', '-o', help='Save analysis to JSON file')
@click.option('--detailed', is_flag=True, help='Show detailed analysis')
@click.pass_context
def analyze_calendar(ctx, calendar_name: str, output: Optional[str], detailed: bool):
    """Analyze a Change Calendar and provide insights."""
    config = ctx.obj['config']
    
    try:
        # Initialize Change Calendar Manager
        aws_config = config.get_aws_config()
        manager = ChangeCalendarManager(
            region_name=aws_config.get('region', 'ap-northeast-1'),
            profile_name=aws_config.get('profile')
        )
        
        click.echo(f"Analyzing Change Calendar: {calendar_name}")
        
        # Perform analysis
        analysis = manager.analyze_calendar(calendar_name)
        
        # Display basic information
        basic_stats = analysis['basic_stats']
        click.echo(f"\n📊 Basic Statistics:")
        click.echo(f"  Total Events: {basic_stats['total_events']}")
        click.echo(f"  Content Size: {basic_stats['content_size']} characters")
        
        if basic_stats.get('date_range'):
            date_range = basic_stats['date_range']
            click.echo(f"  Date Range: {date_range['start_date']} to {date_range['end_date']}")
            click.echo(f"  Span: {date_range['span_days']} days")
        
        # Display event analysis
        event_analysis = analysis['event_analysis']
        click.echo(f"\n📅 Event Analysis:")
        click.echo(f"  Japanese Holidays: {event_analysis['japanese_holidays_count']}")
        click.echo(f"  Custom Events: {event_analysis['custom_events_count']}")
        
        if event_analysis['event_types']:
            click.echo(f"  Event Types:")
            for event_type, count in event_analysis['event_types'].items():
                click.echo(f"    - {event_type}: {count}")
        
        # Display upcoming events
        upcoming = event_analysis.get('upcoming_events', [])
        if upcoming:
            click.echo(f"\n📆 Upcoming Events (next 30 days):")
            for event in upcoming[:5]:
                click.echo(f"  {event['date']} ({event['days_until']} days) - {event['summary']}")
        
        # Display coverage analysis
        coverage = analysis['coverage_analysis']
        click.echo(f"\n📈 Coverage Analysis:")
        click.echo(f"  Coverage: {coverage['coverage_percentage']}%")
        click.echo(f"  Covered Days: {coverage['covered_days']}/{coverage['total_days']}")
        
        # Display recommendations
        recommendations = analysis['recommendations']
        if recommendations:
            click.echo(f"\n💡 Recommendations:")
            for i, rec in enumerate(recommendations, 1):
                click.echo(f"  {i}. {rec}")
        
        # Show detailed analysis if requested
        if detailed:
            time_analysis = analysis['time_analysis']
            
            click.echo(f"\n📊 Detailed Time Analysis:")
            
            # Monthly distribution
            monthly = time_analysis.get('monthly_distribution', {})
            if monthly:
                click.echo(f"  Monthly Distribution:")
                for month, count in monthly.items():
                    click.echo(f"    {month}: {count} events")
            
            # Weekday distribution
            weekday = time_analysis.get('weekday_distribution', {})
            if weekday:
                click.echo(f"  Weekday Distribution:")
                for day, count in weekday.items():
                    click.echo(f"    {day}: {count} events")
            
            # Duration statistics
            duration = time_analysis.get('duration_statistics', {})
            if duration:
                click.echo(f"  Duration Statistics:")
                click.echo(f"    Average Duration: {duration.get('average_duration', 0):.1f} days")
                click.echo(f"    Total Blocked Days: {duration.get('total_blocked_days', 0)} days")
            
            # Gaps and busy periods
            gaps = coverage.get('gaps', [])
            if gaps:
                click.echo(f"  Coverage Gaps:")
                for gap in gaps:
                    click.echo(f"    {gap['start_date']} to {gap['end_date']} ({gap['gap_days']} days)")
            
            busy_periods = coverage.get('busy_periods', [])
            if busy_periods:
                click.echo(f"  Busy Periods:")
                for period in busy_periods:
                    click.echo(f"    {period['start_date']} to {period['end_date']} ({period['duration_days']} days)")
        
        # Save to file if requested
        if output:
            with open(output, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, ensure_ascii=False, indent=2, default=str)
            click.echo(f"\n💾 Analysis saved to: {output}")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument('calendar_names', nargs=-1, required=True)
@click.option('--output', '-o', help='Save comparison to JSON file')
@click.pass_context
def compare_calendars(ctx, calendar_names: tuple, output: Optional[str]):
    """Compare multiple Change Calendars."""
    config = ctx.obj['config']
    
    try:
        if len(calendar_names) < 2:
            click.echo("Error: At least 2 calendars are required for comparison", err=True)
            raise click.Abort()
        
        # Initialize Change Calendar Manager
        aws_config = config.get_aws_config()
        manager = ChangeCalendarManager(
            region_name=aws_config.get('region', 'ap-northeast-1'),
            profile_name=aws_config.get('profile')
        )
        
        click.echo(f"Comparing {len(calendar_names)} Change Calendars...")
        
        # Perform comparison
        comparison = manager.compare_calendars(list(calendar_names))
        
        # Display comparison results
        click.echo(f"\n📊 Calendar Comparison:")
        
        summary = comparison['comparison_summary']
        
        # Event counts comparison
        click.echo(f"  Event Counts:")
        for calendar, count in summary['event_counts'].items():
            click.echo(f"    {calendar}: {count} events")
        
        # Coverage comparison
        click.echo(f"  Coverage Comparison:")
        for calendar, coverage in summary['coverage_comparison'].items():
            click.echo(f"    {calendar}: {coverage}%")
        
        # Holiday coverage comparison
        click.echo(f"  Japanese Holiday Coverage:")
        for calendar, holidays in summary['holiday_coverage'].items():
            click.echo(f"    {calendar}: {holidays} holidays")
        
        # Recommendations
        if summary.get('recommendations'):
            click.echo(f"\n💡 Comparison Recommendations:")
            for i, rec in enumerate(summary['recommendations'], 1):
                click.echo(f"  {i}. {rec}")
        
        # Save to file if requested
        if output:
            with open(output, 'w', encoding='utf-8') as f:
                json.dump(comparison, f, ensure_ascii=False, indent=2, default=str)
            click.echo(f"\n💾 Comparison saved to: {output}")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option('--operation', help='Filter by operation name')
@click.option('--hours', type=int, default=1, help='Time window in hours (default: 1)')
@click.pass_context
def performance_stats(ctx, operation: Optional[str], hours: int):
    """Show performance statistics."""
    logging_manager = ctx.obj.get('logging_manager')
    if not logging_manager:
        click.echo("Performance monitoring is not enabled", err=True)
        return
    
    from datetime import timedelta
    time_window = timedelta(hours=hours)
    
    try:
        stats = logging_manager.get_performance_summary(operation, time_window)
        
        if stats.get('total_operations', 0) == 0:
            click.echo(f"No performance data found for the last {hours} hour(s)")
            return
        
        click.echo(f"Performance Statistics (last {hours} hour(s)):")
        if operation:
            click.echo(f"  Operation: {operation}")
        
        click.echo(f"  Total Operations: {stats['total_operations']}")
        click.echo(f"  Success Rate: {stats['success_rate']:.1f}%")
        click.echo(f"  Successful: {stats['success_count']}")
        click.echo(f"  Failed: {stats['error_count']}")
        
        duration_stats = stats['duration_stats']
        click.echo(f"  Duration Statistics:")
        click.echo(f"    Min: {duration_stats['min']:.3f}s")
        click.echo(f"    Max: {duration_stats['max']:.3f}s")
        click.echo(f"    Average: {duration_stats['avg']:.3f}s")
        click.echo(f"    Total: {duration_stats['total']:.3f}s")
        
        memory_stats = stats['memory_stats']
        click.echo(f"  Memory Statistics:")
        click.echo(f"    Min Delta: {memory_stats['min_delta']:+.2f}MB")
        click.echo(f"    Max Delta: {memory_stats['max_delta']:+.2f}MB")
        click.echo(f"    Average Delta: {memory_stats['avg_delta']:+.2f}MB")
        click.echo(f"    Total Delta: {memory_stats['total_delta']:+.2f}MB")
        
        cpu_stats = stats['cpu_stats']
        click.echo(f"  CPU Statistics:")
        click.echo(f"    Min: {cpu_stats['min']:.1f}%")
        click.echo(f"    Max: {cpu_stats['max']:.1f}%")
        click.echo(f"    Average: {cpu_stats['avg']:.1f}%")
        
    except Exception as e:
        click.echo(f"Error retrieving performance statistics: {e}", err=True)


@cli.command()
@click.pass_context
def system_metrics(ctx):
    """Show current system metrics."""
    logging_manager = ctx.obj.get('logging_manager')
    if not logging_manager:
        click.echo("System monitoring is not enabled", err=True)
        return
    
    try:
        metrics = logging_manager.get_system_metrics()
        if not metrics:
            click.echo("System metrics not available", err=True)
            return
        
        click.echo("Current System Metrics:")
        click.echo(f"  CPU Usage: {metrics.cpu_percent:.1f}%")
        click.echo(f"  Memory Usage: {metrics.memory_percent:.1f}% ({metrics.memory_used_mb:.0f}MB used)")
        click.echo(f"  Memory Available: {metrics.memory_available_mb:.0f}MB")
        click.echo(f"  Disk Usage: {metrics.disk_usage_percent:.1f}% ({metrics.disk_free_gb:.1f}GB free)")
        click.echo(f"  Active Threads: {metrics.active_threads}")
        click.echo(f"  Process ID: {metrics.process_id}")
        click.echo(f"  Timestamp: {metrics.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        click.echo(f"Error retrieving system metrics: {e}", err=True)


@cli.command()
@click.confirmation_option(prompt='Are you sure you want to enable debug mode?')
@click.pass_context
def enable_debug(ctx):
    """Enable debug mode with verbose logging."""
    try:
        set_debug_mode(True)
        click.echo("Debug mode enabled. Verbose logging is now active.")
    except Exception as e:
        click.echo(f"Error enabling debug mode: {e}", err=True)


@cli.command()
@click.pass_context
def disable_debug(ctx):
    """Disable debug mode."""
    try:
        set_debug_mode(False)
        click.echo("Debug mode disabled. Normal logging restored.")
    except Exception as e:
        click.echo(f"Error disabling debug mode: {e}", err=True)


@cli.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--format', '-f', type=click.Choice(['human', 'json', 'csv', 'simple']), 
              default='human', help='Output format (default: human)')
@click.option('--output', '-o', help='Save output to file')
@click.pass_context
@log_performance("analyze_ics")
@log_function_call(log_args=True)
def analyze_ics(ctx, file_path: str, format: str, output: Optional[str]):
    """Analyze ICS file and display contents in human-readable format.
    
    要件3: ICSファイル解析・可視化
    
    Examples:
      python main.py analyze-ics calendar.ics
      python main.py analyze-ics calendar.ics --format json -o analysis.json
      python main.py analyze-ics calendar.ics --format simple
    """
    logging_manager = ctx.obj.get('logging_manager')
    
    with logging_manager.monitor_operation("analyze_ics", {
        "file_path": file_path,
        "format": format
    }) if logging_manager else nullcontext():
        try:
            click.echo(f"Analyzing ICS file: {file_path}")
            
            # Initialize ICS analyzer
            analyzer = ICSAnalyzer()
            
            # Parse and analyze the ICS file
            analysis_result = analyzer.parse_ics_file(file_path)
            
            # Format output based on requested format
            if format == 'human':
                formatted_output = analyzer.format_human_readable(analysis_result)
            elif format == 'json':
                formatted_output = analyzer.export_json(analysis_result)
            elif format == 'csv':
                formatted_output = analyzer.export_csv(analysis_result['events'])
            elif format == 'simple':
                formatted_output = analyzer.format_simple_output(analysis_result)
            else:
                formatted_output = analyzer.format_human_readable(analysis_result)
            
            # Output to file or console
            if output:
                with open(output, 'w', encoding='utf-8') as f:
                    f.write(formatted_output)
                click.echo(f"Analysis saved to: {output}")
            else:
                click.echo(formatted_output)
            
            # Show summary statistics
            stats = analysis_result['statistics']
            validation_errors = analysis_result['validation_errors']
            
            click.echo(f"\n✅ Analysis complete:")
            click.echo(f"  Total events: {stats['total_events']}")
            if validation_errors:
                click.echo(f"  ⚠️  Validation errors: {len(validation_errors)}")
            else:
                click.echo(f"  ✅ No validation errors")
                
        except Exception as e:
            error_msg = f"Failed to analyze ICS file: {e}"
            click.echo(f"Error: {error_msg}", err=True)
            raise click.Abort()


@cli.command()
@click.argument('file1', type=click.Path(exists=True))
@click.argument('file2', type=click.Path(exists=True))
@click.option('--format', '-f', type=click.Choice(['human', 'json']), 
              default='human', help='Output format (default: human)')
@click.option('--output', '-o', help='Save comparison to file')
@click.pass_context
@log_performance("compare_ics")
@log_function_call(log_args=True)
def compare_ics(ctx, file1: str, file2: str, format: str, output: Optional[str]):
    """Compare two ICS files and show differences.
    
    要件4: ICSファイル比較・差分表示
    
    Examples:
      python main.py compare-ics old.ics new.ics
      python main.py compare-ics old.ics new.ics --format json -o comparison.json
    """
    logging_manager = ctx.obj.get('logging_manager')
    
    with logging_manager.monitor_operation("compare_ics", {
        "file1": file1,
        "file2": file2,
        "format": format
    }) if logging_manager else nullcontext():
        try:
            click.echo(f"Comparing ICS files: {file1} vs {file2}")
            
            # Initialize ICS analyzer
            analyzer = ICSAnalyzer()
            
            # Compare the ICS files
            comparison_result = analyzer.compare_ics_files(file1, file2)
            
            # Format output based on requested format
            if format == 'human':
                formatted_output = analyzer.format_comparison_result(comparison_result)
            elif format == 'json':
                formatted_output = analyzer.export_comparison_json(comparison_result)
            else:
                formatted_output = analyzer.format_comparison_result(comparison_result)
            
            # Output to file or console
            if output:
                with open(output, 'w', encoding='utf-8') as f:
                    f.write(formatted_output)
                click.echo(f"Comparison saved to: {output}")
            else:
                click.echo(formatted_output)
            
            # Show summary statistics
            summary = comparison_result['summary']
            click.echo(f"\n✅ Comparison complete:")
            click.echo(f"  Added: {summary['added']} events")
            click.echo(f"  Deleted: {summary['deleted']} events")
            click.echo(f"  Modified: {summary['modified']} events")
            click.echo(f"  Unchanged: {summary['unchanged']} events")
                
        except Exception as e:
            error_msg = f"Failed to compare ICS files: {e}"
            click.echo(f"Error: {error_msg}", err=True)
            raise click.Abort()


@cli.command()
@click.argument('file1', type=click.Path(exists=True))
@click.argument('file2', type=click.Path(exists=True))
@click.option('--color/--no-color', default=True, help='Use color output (default: enabled)')
@click.option('--output', '-o', help='Save semantic diff to file')
@click.pass_context
@log_performance("semantic_diff")
@log_function_call(log_args=True)
def semantic_diff(ctx, file1: str, file2: str, color: bool, output: Optional[str]):
    """Generate semantic diff comparison between two ICS files.
    
    要件4.2: イベント意味的Diff形式比較表示
    
    Shows detailed event-level differences with symbols:
      + Added events
      - Deleted events  
      ~ Modified events
      = Moved events
      Δ Duration changed events
    
    Examples:
      python main.py semantic-diff old.ics new.ics
      python main.py semantic-diff old.ics new.ics --no-color -o diff.txt
    """
    logging_manager = ctx.obj.get('logging_manager')
    
    with logging_manager.monitor_operation("semantic_diff", {
        "file1": file1,
        "file2": file2,
        "color": color
    }) if logging_manager else nullcontext():
        try:
            click.echo(f"Generating semantic diff: {file1} vs {file2}")
            
            # Initialize ICS analyzer
            analyzer = ICSAnalyzer()
            
            # Generate semantic diff
            diff_result = analyzer.generate_event_semantic_diff(file1, file2)
            
            # Format semantic diff output
            formatted_diff = analyzer.format_semantic_diff(diff_result, use_color=color)
            
            # Output to file or console
            if output:
                # Remove color codes when saving to file
                if color:
                    import re
                    # Remove ANSI color codes
                    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
                    clean_diff = ansi_escape.sub('', formatted_diff)
                    analyzer.export_semantic_diff_file(clean_diff, output)
                else:
                    analyzer.export_semantic_diff_file(formatted_diff, output)
                click.echo(f"Semantic diff saved to: {output}")
            else:
                click.echo(formatted_diff)
            
            # Show summary statistics
            statistics = diff_result['statistics']
            click.echo(f"\n✅ Semantic diff complete:")
            click.echo(f"  + Added: {statistics['added']} events")
            click.echo(f"  - Deleted: {statistics['deleted']} events")
            click.echo(f"  ~ Modified: {statistics['modified']} events")
            click.echo(f"  = Moved: {statistics['moved']} events")
            click.echo(f"  Δ Duration changed: {statistics['duration_changed']} events")
                
        except Exception as e:
            error_msg = f"Failed to generate semantic diff: {e}"
            click.echo(f"Error: {error_msg}", err=True)
            raise click.Abort()


def cleanup_on_exit():
    """Cleanup function called on application exit."""
    try:
        cleanup_logging()
    except Exception:
        pass  # Ignore cleanup errors


import atexit
atexit.register(cleanup_on_exit)


if __name__ == '__main__':
    cli()