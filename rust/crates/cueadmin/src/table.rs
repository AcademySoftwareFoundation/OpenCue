// Copyright Contributors to the OpenCue Project
//
// Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
// in compliance with the License. You may obtain a copy of the License at
//
// http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software distributed under the License
// is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
// or implied. See the License for the specific language governing permissions and limitations under
// the License.

//! Mode-independent tables, rendered either as boxed tables for people or as tab-separated values
//! for scripts.
//!
//! A [`Table`] holds both renderings of every cell, since the two differ in more than layout:
//! pretty cells are humanized (`2.0G`, `3d 4h`) and may merge fields (`4.5 / 16`), while raw cells
//! keep exact values (KB, epoch seconds) in columns of their own.

use std::borrow::Cow;
use std::fmt::{Display, Write};
use std::io::IsTerminal;

use comfy_table::{Attribute, CellAlignment, Color, ContentArrangement};

/// Rounded borders with a single header rule and no lines between rows.
const BOX_STYLE: &str = "││──├─┼┤│    ┬┴╭╮╰╯";

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Align {
    Left,
    Right,
}

/// Where a column appears.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Visibility {
    /// Pretty and raw.
    Both,
    /// Pretty with `--wide`, and raw.
    Wide,
    /// Pretty only, usually a merge of raw columns.
    Pretty,
    /// Raw only.
    Raw,
}

/// A column definition: a pretty header and/or a raw key.
#[derive(Debug, Clone, Copy)]
pub struct Column {
    header: &'static str,
    key: &'static str,
    align: Align,
    visibility: Visibility,
}

impl Column {
    /// A column shown in both modes.
    pub const fn new(header: &'static str, key: &'static str) -> Self {
        Self {
            header,
            key,
            align: Align::Left,
            visibility: Visibility::Both,
        }
    }

    /// A column shown only in pretty mode.
    pub const fn pretty(header: &'static str) -> Self {
        Self {
            visibility: Visibility::Pretty,
            ..Self::new(header, "")
        }
    }

    /// A column shown only in raw mode.
    pub const fn raw(key: &'static str) -> Self {
        Self {
            visibility: Visibility::Raw,
            ..Self::new("", key)
        }
    }

    /// Right-aligns the column in pretty mode.
    pub const fn right(mut self) -> Self {
        self.align = Align::Right;
        self
    }

    /// Hides the column in pretty mode unless `--wide` is given.
    pub const fn wide(mut self) -> Self {
        self.visibility = Visibility::Wide;
        self
    }

    fn shown(&self, raw: bool, wide: bool) -> bool {
        match self.visibility {
            Visibility::Both => true,
            Visibility::Wide => raw || wide,
            Visibility::Pretty => !raw,
            Visibility::Raw => raw,
        }
    }
}

/// How a pretty cell is colored.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum Tone {
    #[default]
    Plain,
    Good,
    Warn,
    Bad,
    Dim,
}

/// One value, in its pretty and raw forms.
#[derive(Debug, Clone, Default)]
pub struct Cell {
    text: String,
    raw: String,
    tone: Tone,
}

impl Cell {
    /// A cell with different pretty and raw text.
    pub fn new(text: impl Into<String>, raw: impl Display) -> Self {
        Self {
            text: text.into(),
            raw: raw.to_string(),
            tone: Tone::Plain,
        }
    }

    /// A cell that reads the same in both modes.
    pub fn same(value: impl Display) -> Self {
        let value = value.to_string();
        Self::new(value.clone(), value)
    }

    /// A cell for a pretty-only column.
    pub fn pretty(text: impl Into<String>) -> Self {
        Self::new(text, "")
    }

    /// A cell for a raw-only column.
    pub fn raw(value: impl Display) -> Self {
        Self::new("", value)
    }

    pub fn tone(mut self, tone: Tone) -> Self {
        self.tone = tone;
        self
    }
}

/// What the rows of a table are, for the footer and the empty-state message.
#[derive(Debug, Clone, Copy)]
pub struct Noun {
    pub one: &'static str,
    pub many: &'static str,
}

/// A table ready to be rendered in either mode.
#[derive(Debug, Clone)]
pub struct Table {
    noun: Noun,
    title: Option<String>,
    columns: Vec<Column>,
    rows: Vec<Vec<Cell>>,
    totals: Option<Vec<Cell>>,
}

impl Table {
    pub fn new(noun: Noun, columns: &[Column]) -> Self {
        Self {
            noun,
            title: None,
            columns: columns.to_vec(),
            rows: Vec::new(),
            totals: None,
        }
    }

    /// Sets a heading printed above the pretty table.
    pub fn title(mut self, title: impl Into<String>) -> Self {
        self.title = Some(title.into());
        self
    }

    /// Adds a row. It must have one cell per column.
    pub fn row(&mut self, cells: Vec<Cell>) {
        debug_assert_eq!(cells.len(), self.columns.len(), "row/column count mismatch");
        self.rows.push(cells);
    }

    /// Sets a totals row, shown only in pretty mode and only when there are rows. Empty cells
    /// are fine for columns that don't add up.
    pub fn totals(&mut self, cells: Vec<Cell>) {
        debug_assert_eq!(
            cells.len(),
            self.columns.len(),
            "totals/column count mismatch"
        );
        self.totals = Some(cells);
    }

    /// Appends the rows of `other`, which must have the same columns.
    pub fn extend(&mut self, other: Table) {
        self.rows.extend(other.rows);
    }

    fn visible(&self, raw: bool, wide: bool) -> Vec<usize> {
        (0..self.columns.len())
            .filter(|&i| self.columns[i].shown(raw, wide))
            .collect()
    }

    /// Renders as tab-separated values: a header of keys, then one line per row, every column.
    pub fn to_raw(&self) -> String {
        let columns = self.visible(true, true);
        let mut out = String::new();
        let line = |out: &mut String, values: Vec<Cow<str>>| {
            let _ = writeln!(out, "{}", values.join("\t"));
        };
        line(
            &mut out,
            columns
                .iter()
                .map(|&i| self.columns[i].key.into())
                .collect(),
        );
        for row in &self.rows {
            line(
                &mut out,
                columns.iter().map(|&i| sanitize(&row[i].raw)).collect(),
            );
        }
        out
    }

    /// Renders as a boxed table with a count footer, or a one-line message when empty.
    pub fn to_pretty(&self, wide: bool, color: bool) -> String {
        let mut out = String::new();
        if let Some(title) = &self.title {
            let _ = writeln!(out, "{}", paint(title, Tone::Plain, true, color));
        }
        if self.rows.is_empty() {
            let _ = writeln!(out, "No {} found.", self.noun.many);
            return out;
        }

        let columns = self.visible(false, wide);
        let mut table = comfy_table::Table::new();
        table
            .load_preset(BOX_STYLE)
            .set_content_arrangement(ContentArrangement::Dynamic);
        if color {
            table.enforce_styling();
        }
        table.set_header(columns.iter().map(|&i| {
            let cell = comfy_table::Cell::new(self.columns[i].header);
            if color {
                cell.add_attribute(Attribute::Bold)
            } else {
                cell
            }
        }));
        let to_cells = |row: &[Cell], bold: bool| -> Vec<comfy_table::Cell> {
            columns
                .iter()
                .map(|&i| styled(&row[i], self.columns[i].align, bold, color))
                .collect()
        };
        for row in &self.rows {
            table.add_row(to_cells(row, false));
        }
        if let Some(totals) = &self.totals {
            table.add_row(to_cells(totals, true));
        }
        for (column, &i) in table.column_iter_mut().zip(&columns) {
            if self.columns[i].align == Align::Right {
                column.set_cell_alignment(CellAlignment::Right);
            }
        }

        let _ = writeln!(out, "{table}");
        let noun = if self.rows.len() == 1 {
            self.noun.one
        } else {
            self.noun.many
        };
        let footer = format!("{} {noun}", self.rows.len());
        let _ = writeln!(out, "{}", paint(&footer, Tone::Dim, false, color));
        out
    }
}

/// Tabs and newlines would break the raw layout.
fn sanitize(value: &str) -> Cow<'_, str> {
    if value.contains(['\t', '\n']) {
        value.replace(['\t', '\n'], " ").into()
    } else {
        value.into()
    }
}

fn styled(cell: &Cell, align: Align, bold: bool, color: bool) -> comfy_table::Cell {
    let mut out = comfy_table::Cell::new(&cell.text);
    if align == Align::Right {
        out = out.set_alignment(CellAlignment::Right);
    }
    if !color {
        return out;
    }
    if bold {
        out = out.add_attribute(Attribute::Bold);
    }
    match tone_color(cell.tone) {
        Some(c) => out.fg(c),
        None if cell.tone == Tone::Dim => out.add_attribute(Attribute::Dim),
        None => out,
    }
}

fn tone_color(tone: Tone) -> Option<Color> {
    match tone {
        Tone::Good => Some(Color::Green),
        Tone::Warn => Some(Color::Yellow),
        Tone::Bad => Some(Color::Red),
        Tone::Plain | Tone::Dim => None,
    }
}

/// Wraps `text` in ANSI codes for `tone`, or returns it untouched without color.
pub fn paint(text: &str, tone: Tone, bold: bool, color: bool) -> String {
    if !color {
        return text.to_string();
    }
    let mut codes = Vec::new();
    if bold {
        codes.push("1");
    }
    match tone {
        Tone::Good => codes.push("32"),
        Tone::Warn => codes.push("33"),
        Tone::Bad => codes.push("31"),
        Tone::Dim => codes.push("2"),
        Tone::Plain => {}
    }
    if codes.is_empty() {
        return text.to_string();
    }
    format!("\x1b[{}m{text}\x1b[0m", codes.join(";"))
}

/// Output settings for a run: the mode and whether to color.
#[derive(Debug, Clone, Copy)]
pub struct Printer {
    pub raw: bool,
    pub color: bool,
}

impl Printer {
    /// Colors only when stdout is a terminal and `NO_COLOR` is unset or empty.
    pub fn new(raw: bool) -> Self {
        let no_color = std::env::var_os("NO_COLOR").is_some_and(|v| !v.is_empty());
        Self {
            raw,
            color: !raw && !no_color && std::io::stdout().is_terminal(),
        }
    }

    pub fn render(&self, table: &Table, wide: bool) -> String {
        if self.raw {
            table.to_raw()
        } else {
            table.to_pretty(wide, self.color)
        }
    }

    pub fn table(&self, table: &Table, wide: bool) {
        print!("{}", self.render(table, wide));
    }

    /// Reports a completed action. Silent in raw mode.
    pub fn done(&self, message: impl Display) {
        if !self.raw {
            println!("{} {message}", paint("✓", Tone::Good, false, self.color));
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const NOUN: Noun = Noun {
        one: "thing",
        many: "things",
    };

    fn sample() -> Table {
        let mut table = Table::new(
            NOUN,
            &[
                Column::new("Name", "name"),
                Column::new("Size", "size_kb").right(),
                Column::new("Extra", "extra").wide(),
                Column::pretty("Merged"),
                Column::raw("exact"),
            ],
        );
        table.row(vec![
            Cell::same("alpha"),
            Cell::new("2.0G", 2_097_152),
            Cell::same("x"),
            Cell::pretty("a / b"),
            Cell::raw(42),
        ]);
        table
    }

    #[test]
    fn raw_has_every_column_but_pretty_ones() {
        assert_eq!(
            sample().to_raw(),
            "name\tsize_kb\textra\texact\nalpha\t2097152\tx\t42\n"
        );
    }

    #[test]
    fn raw_values_stay_on_one_line() {
        let mut table = Table::new(NOUN, &[Column::new("Name", "name")]);
        table.row(vec![Cell::same("a\tb\nc")]);
        assert_eq!(table.to_raw(), "name\na b c\n");
    }

    #[test]
    fn pretty_hides_wide_and_raw_columns() {
        let out = sample().to_pretty(false, false);
        assert!(out.starts_with('╭'), "{out}");
        assert!(out.contains("Merged") && out.contains("a / b"));
        assert!(!out.contains("Extra") && !out.contains("42"));
        assert!(out.contains("2.0G"));
        assert!(out.ends_with("1 thing\n"));

        let wide = sample().to_pretty(true, false);
        assert!(wide.contains("Extra"));
    }

    #[test]
    fn pretty_right_aligns() {
        let mut table = Table::new(NOUN, &[Column::new("Size", "size").right()]);
        table.row(vec![Cell::same("1")]);
        table.row(vec![Cell::same("100")]);
        let out = table.to_pretty(false, false);
        assert!(out.contains("│    1 │"), "{out}");
    }

    #[test]
    fn pretty_totals_and_title() {
        let mut table = Table::new(NOUN, &[Column::new("Name", "n"), Column::new("N", "n")])
            .title("Things for pipe");
        table.row(vec![Cell::same("a"), Cell::same(1)]);
        table.row(vec![Cell::same("b"), Cell::same(2)]);
        table.totals(vec![Cell::pretty("Total"), Cell::pretty("3")]);
        let out = table.to_pretty(false, false);
        assert!(out.starts_with("Things for pipe\n╭"));
        assert!(out.contains("Total"));
        assert!(out.ends_with("2 things\n"));
        assert!(!table.to_raw().contains("Total"));
    }

    #[test]
    fn empty_tables() {
        let table = Table::new(NOUN, &[Column::new("Name", "name")]);
        assert_eq!(table.to_pretty(false, false), "No things found.\n");
        assert_eq!(table.to_raw(), "name\n");
    }

    #[test]
    fn color_only_when_asked() {
        let mut table = Table::new(NOUN, &[Column::new("State", "state")]);
        table.row(vec![Cell::same("UP").tone(Tone::Good)]);
        assert!(!table.to_pretty(false, false).contains('\x1b'));
        assert!(table.to_pretty(false, true).contains('\x1b'));
        assert_eq!(paint("x", Tone::Plain, false, true), "x");
        assert_eq!(paint("x", Tone::Bad, true, true), "\x1b[1;31mx\x1b[0m");
    }
}
