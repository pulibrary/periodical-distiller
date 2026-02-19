"""Tests for pipeline infrastructure."""

import json
from pathlib import Path

import pytest

from periodical_distiller.pipeline import Token, Pipe, Filter, Pipeline, load_token, dump_token


class TestToken:
    """Tests for Token class."""

    def test_token_creation(self):
        """Token can be created with content dict."""
        content = {"id": "12345", "data": "test"}
        token = Token(content)
        assert token.content == content

    def test_token_name_returns_id(self):
        """Token.name returns the 'id' field."""
        token = Token({"id": "article-123"})
        assert token.name == "article-123"

    def test_token_name_returns_none_when_no_id(self):
        """Token.name returns None when no id field."""
        token = Token({"other": "data"})
        assert token.name is None

    def test_token_get_prop(self):
        """Token.get_prop retrieves properties."""
        token = Token({"id": "123", "status": "pending"})
        assert token.get_prop("status") == "pending"
        assert token.get_prop("missing") is None

    def test_token_put_prop(self):
        """Token.put_prop sets properties."""
        token = Token({"id": "123"})
        token.put_prop("html_path", "/path/to/file.html")
        assert token.get_prop("html_path") == "/path/to/file.html"

    def test_token_repr(self):
        """Token repr includes the name."""
        token = Token({"id": "test-123"})
        assert repr(token) == "Token(test-123)"

    def test_token_write_log(self):
        """Token.write_log appends to log list."""
        token = Token({"id": "123"})
        token.write_log("Processing started", level="INFO", stage="html_filter")

        assert "log" in token.content
        assert len(token.content["log"]) == 1

        entry = token.content["log"][0]
        assert entry["message"] == "Processing started"
        assert entry["level"] == "INFO"
        assert entry["stage"] == "html_filter"
        assert "timestamp" in entry

    def test_token_write_log_creates_log_list(self):
        """Token.write_log creates log list if not present."""
        token = Token({"id": "123"})
        assert "log" not in token.content

        token.write_log("First entry")
        assert "log" in token.content
        assert len(token.content["log"]) == 1


class TestLoadDumpToken:
    """Tests for token serialization."""

    def test_load_token(self, tmp_path):
        """load_token reads token from JSON file."""
        token_file = tmp_path / "test.json"
        token_file.write_text(json.dumps({"id": "123", "data": "test"}))

        token = load_token(token_file)
        assert token.name == "123"
        assert token.get_prop("data") == "test"

    def test_dump_token(self, tmp_path):
        """dump_token writes token to JSON file."""
        token = Token({"id": "456", "status": "complete"})
        dest = tmp_path / "output.json"

        dump_token(token, dest)

        assert dest.exists()
        data = json.loads(dest.read_text())
        assert data["id"] == "456"
        assert data["status"] == "complete"


class TestPipe:
    """Tests for Pipe class."""

    def test_pipe_creation(self, tmp_path):
        """Pipe can be created with input/output paths."""
        in_path = tmp_path / "input"
        out_path = tmp_path / "output"
        in_path.mkdir()
        out_path.mkdir()

        pipe = Pipe(in_path, out_path)
        assert pipe.input == in_path
        assert pipe.output == out_path
        assert pipe.token is None

    def test_pipe_repr(self, tmp_path):
        """Pipe repr shows paths."""
        pipe = Pipe(tmp_path / "in", tmp_path / "out")
        assert "in" in repr(pipe)
        assert "out" in repr(pipe)

    def test_pipe_list_input_tokens(self, tmp_path):
        """Pipe.list_input_tokens returns all tokens in input bucket."""
        in_path = tmp_path / "input"
        out_path = tmp_path / "output"
        in_path.mkdir()
        out_path.mkdir()

        # Create some token files
        (in_path / "token1.json").write_text(json.dumps({"id": "token1"}))
        (in_path / "token2.json").write_text(json.dumps({"id": "token2"}))

        pipe = Pipe(in_path, out_path)
        tokens = pipe.list_input_tokens()

        assert len(tokens) == 2
        names = {t.name for t in tokens}
        assert names == {"token1", "token2"}

    def test_pipe_take_token(self, tmp_path):
        """Pipe.take_token gets and marks a token."""
        in_path = tmp_path / "input"
        out_path = tmp_path / "output"
        in_path.mkdir()
        out_path.mkdir()

        (in_path / "article.json").write_text(json.dumps({"id": "article"}))

        pipe = Pipe(in_path, out_path)
        token = pipe.take_token()

        assert token is not None
        assert token.name == "article"
        assert pipe.token == token
        # Original file should be renamed to .bak
        assert not (in_path / "article.json").exists()
        assert (in_path / "article.bak").exists()

    def test_pipe_take_token_by_id(self, tmp_path):
        """Pipe.take_token can take a specific token by id."""
        in_path = tmp_path / "input"
        out_path = tmp_path / "output"
        in_path.mkdir()
        out_path.mkdir()

        (in_path / "first.json").write_text(json.dumps({"id": "first"}))
        (in_path / "second.json").write_text(json.dumps({"id": "second"}))

        pipe = Pipe(in_path, out_path)
        token = pipe.take_token(id="second")

        assert token.name == "second"

    def test_pipe_take_token_returns_none_when_empty(self, tmp_path):
        """Pipe.take_token returns None when no tokens available."""
        in_path = tmp_path / "input"
        out_path = tmp_path / "output"
        in_path.mkdir()
        out_path.mkdir()

        pipe = Pipe(in_path, out_path)
        token = pipe.take_token()

        assert token is None

    def test_pipe_put_token(self, tmp_path):
        """Pipe.put_token moves token to output bucket."""
        in_path = tmp_path / "input"
        out_path = tmp_path / "output"
        in_path.mkdir()
        out_path.mkdir()

        (in_path / "article.json").write_text(json.dumps({"id": "article"}))

        pipe = Pipe(in_path, out_path)
        pipe.take_token()
        pipe.put_token()

        # Token should be in output, not input
        assert not (in_path / "article.json").exists()
        assert not (in_path / "article.bak").exists()
        assert (out_path / "article.json").exists()
        assert pipe.token is None

    def test_pipe_put_token_with_error(self, tmp_path):
        """Pipe.put_token with error_flag creates .err file."""
        in_path = tmp_path / "input"
        out_path = tmp_path / "output"
        in_path.mkdir()
        out_path.mkdir()

        (in_path / "article.json").write_text(json.dumps({"id": "article"}))

        pipe = Pipe(in_path, out_path)
        pipe.take_token()
        pipe.put_token(error_flag=True)

        # Token should have .err extension in input
        assert (in_path / "article.err").exists()
        assert not (out_path / "article.json").exists()

    def test_pipe_put_token_back(self, tmp_path):
        """Pipe.put_token_back returns token to input bucket."""
        in_path = tmp_path / "input"
        out_path = tmp_path / "output"
        in_path.mkdir()
        out_path.mkdir()

        (in_path / "article.json").write_text(json.dumps({"id": "article"}))

        pipe = Pipe(in_path, out_path)
        pipe.take_token()
        pipe.put_token_back()

        # Token should be back in input as .json
        assert (in_path / "article.json").exists()
        assert not (in_path / "article.bak").exists()


class TestFilter:
    """Tests for Filter base class."""

    def test_filter_requires_implementation(self, tmp_path):
        """Filter subclass missing abstract methods cannot be instantiated."""
        in_path = tmp_path / "input"
        out_path = tmp_path / "output"
        in_path.mkdir()
        out_path.mkdir()

        pipe = Pipe(in_path, out_path)

        # A subclass that omits both abstract methods raises TypeError at
        # instantiation time — the ABC machinery catches the gap before any
        # token is ever processed.
        class IncompleteFilter(Filter):
            pass

        with pytest.raises(TypeError):
            IncompleteFilter(pipe)

    def test_filter_recovers_orphaned_tokens(self, tmp_path):
        """Filter recovers .bak files on startup."""
        in_path = tmp_path / "input"
        out_path = tmp_path / "output"
        in_path.mkdir()
        out_path.mkdir()

        # Create an orphaned .bak file
        (in_path / "orphan.bak").write_text(json.dumps({"id": "orphan"}))

        pipe = Pipe(in_path, out_path)

        # Create a concrete filter subclass
        class TestFilter(Filter):
            def process_token(self, token):
                return True

            def validate_token(self, token):
                return True

        # Filter init should recover the orphan
        TestFilter(pipe)

        assert (in_path / "orphan.json").exists()
        assert not (in_path / "orphan.bak").exists()

    def test_filter_run_once_processes_token(self, tmp_path):
        """Filter.run_once processes a single token."""
        in_path = tmp_path / "input"
        out_path = tmp_path / "output"
        in_path.mkdir()
        out_path.mkdir()

        (in_path / "test.json").write_text(json.dumps({"id": "test"}))

        pipe = Pipe(in_path, out_path)

        class TestFilter(Filter):
            def process_token(self, token):
                token.put_prop("processed", True)
                return True

            def validate_token(self, token):
                return True

        f = TestFilter(pipe)
        result = f.run_once()

        assert result is True
        assert (out_path / "test.json").exists()

        # Verify the processed flag was set
        data = json.loads((out_path / "test.json").read_text())
        assert data["processed"] is True

    def test_filter_run_once_returns_false_when_no_tokens(self, tmp_path):
        """Filter.run_once returns False when no tokens available."""
        in_path = tmp_path / "input"
        out_path = tmp_path / "output"
        in_path.mkdir()
        out_path.mkdir()

        pipe = Pipe(in_path, out_path)

        class TestFilter(Filter):
            def process_token(self, token):
                return True

            def validate_token(self, token):
                return True

        f = TestFilter(pipe)
        result = f.run_once()

        assert result is False

    def test_filter_moves_invalid_token_to_error(self, tmp_path):
        """Filter moves tokens that fail validation to .err."""
        in_path = tmp_path / "input"
        out_path = tmp_path / "output"
        in_path.mkdir()
        out_path.mkdir()

        (in_path / "invalid.json").write_text(json.dumps({"id": "invalid"}))

        pipe = Pipe(in_path, out_path)

        class TestFilter(Filter):
            def process_token(self, token):
                return True

            def validate_token(self, token):
                return False  # Always invalid

        f = TestFilter(pipe)
        f.run_once()

        assert (in_path / "invalid.err").exists()
        assert not (out_path / "invalid.json").exists()


class TestPipeline:
    """Tests for Pipeline class."""

    def test_pipeline_creation(self):
        """Pipeline can be created without config."""
        pipeline = Pipeline()
        assert pipeline.buckets == {}

    def test_pipeline_add_bucket(self, tmp_path):
        """Pipeline.add_bucket adds a bucket."""
        pipeline = Pipeline()
        bucket_path = tmp_path / "bucket"
        bucket_path.mkdir()

        pipeline.add_bucket("test", bucket_path)

        assert "test" in pipeline.buckets
        assert pipeline.bucket("test") == bucket_path

    def test_pipeline_bucket_raises_for_unknown(self):
        """Pipeline.bucket raises ValueError for unknown bucket."""
        pipeline = Pipeline()

        with pytest.raises(ValueError, match="no such bucket"):
            pipeline.bucket("nonexistent")

    def test_pipeline_from_config(self, tmp_path):
        """Pipeline can be created from config dict."""
        bucket1 = tmp_path / "bucket1"
        bucket2 = tmp_path / "bucket2"
        bucket1.mkdir()
        bucket2.mkdir()

        config = {
            "buckets": [
                {"name": "input", "path": str(bucket1)},
                {"name": "output", "path": str(bucket2)},
            ]
        }

        pipeline = Pipeline(config)

        assert pipeline.bucket("input") == bucket1
        assert pipeline.bucket("output") == bucket2

    def test_pipeline_pipe(self, tmp_path):
        """Pipeline.pipe creates a Pipe between buckets."""
        bucket1 = tmp_path / "bucket1"
        bucket2 = tmp_path / "bucket2"
        bucket1.mkdir()
        bucket2.mkdir()

        pipeline = Pipeline()
        pipeline.add_bucket("in", bucket1)
        pipeline.add_bucket("out", bucket2)

        pipe = pipeline.pipe("in", "out")

        assert isinstance(pipe, Pipe)
        assert pipe.input == bucket1
        assert pipe.output == bucket2

    def test_pipeline_snapshot(self, tmp_path):
        """Pipeline.snapshot shows bucket status."""
        bucket = tmp_path / "bucket"
        bucket.mkdir()

        (bucket / "waiting.json").write_text("{}")
        (bucket / "error.err").write_text("{}")
        (bucket / "processing.bak").write_text("{}")

        pipeline = Pipeline()
        pipeline.add_bucket("test", bucket)

        snapshot = pipeline.snapshot

        assert "test" in snapshot
        assert "waiting.json" in snapshot["test"]["waiting_tokens"]
        assert "error.err" in snapshot["test"]["errored_tokens"]
        assert "processing.bak" in snapshot["test"]["in_process_tokens"]
