"""
Asset management utilities for CSS/JS minification and bundling.
"""
import os
import hashlib
import json
import time
from pathlib import Path
from flask import current_app, url_for
import re


class AssetManager:
    """Manages CSS/JS assets with minification and bundling."""
    
    def __init__(self, app=None):
        self.app = app
        self.cache = {}
        self.manifest = {}
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize asset manager with Flask app."""
        self.app = app
        
        # Configure asset paths
        app.config.setdefault('ASSET_BUNDLES', {
            'css': {
                'main': [
                    'css/style.css',
                    'css/components/buttons.css',
                    'css/components/forms.css',
                    'css/components/modals.css'
                ],
                'admin': [
                    'css/style.css',
                    'css/admin/dashboard.css',
                    'css/admin/forms.css'
                ],
                'game': [
                    'css/style.css',
                    'css/pages/team_dashboard.css',
                    'css/components/game_board.css'
                ]
            },
            'js': {
                'main': [
                    'js/main.js',
                    'js/components/utils.js'
                ],
                'admin': [
                    'js/main.js',
                    'js/admin/dashboard.js'
                ],
                'game': [
                    'js/main.js',
                    'js/pages/team_dashboard.js'
                ]
            }
        })
        
        app.config.setdefault('ASSET_MINIFY', True)
        app.config.setdefault('ASSET_CACHE_TIMEOUT', 3600)  # 1 hour
        
        # Add template functions
        app.jinja_env.globals['asset_url'] = self.asset_url
        app.jinja_env.globals['bundle_url'] = self.bundle_url
        
        # Load existing manifest
        self.load_manifest()
    
    def get_static_path(self):
        """Get the static files path."""
        return Path(self.app.static_folder)
    
    def get_asset_path(self, asset_path):
        """Get full path to an asset file."""
        return self.get_static_path() / asset_path
    
    def minify_css(self, css_content):
        """
        Minify CSS content.
        
        Args:
            css_content: CSS content string
            
        Returns:
            Minified CSS content
        """
        if not self.app.config.get('ASSET_MINIFY', False):
            return css_content
        
        # Remove comments
        css_content = re.sub(r'/\*.*?\*/', '', css_content, flags=re.DOTALL)
        
        # Remove unnecessary whitespace
        css_content = re.sub(r'\s+', ' ', css_content)
        
        # Remove whitespace around specific characters
        css_content = re.sub(r'\s*([{}:;,>+~])\s*', r'\1', css_content)
        
        # Remove trailing semicolons
        css_content = re.sub(r';}', '}', css_content)
        
        # Remove empty rules
        css_content = re.sub(r'[^{}]+{\s*}', '', css_content)
        
        return css_content.strip()
    
    def minify_js(self, js_content):
        """
        Minify JavaScript content (basic minification).
        
        Args:
            js_content: JavaScript content string
            
        Returns:
            Minified JavaScript content
        """
        if not self.app.config.get('ASSET_MINIFY', False):
            return js_content
        
        # Remove single line comments (but preserve URLs)
        js_content = re.sub(r'(?<!:)//.*$', '', js_content, flags=re.MULTILINE)
        
        # Remove multi-line comments
        js_content = re.sub(r'/\*.*?\*/', '', js_content, flags=re.DOTALL)
        
        # Remove unnecessary whitespace
        js_content = re.sub(r'\s+', ' ', js_content)
        
        # Remove whitespace around specific characters
        js_content = re.sub(r'\s*([{}();,=+\-*/<>!&|])\s*', r'\1', js_content)
        
        return js_content.strip()
    
    def bundle_assets(self, asset_type, bundle_name, asset_list):
        """
        Bundle and minify assets.
        
        Args:
            asset_type: 'css' or 'js'
            bundle_name: Name of the bundle
            asset_list: List of asset file paths
            
        Returns:
            Bundled and minified content
        """
        bundled_content = []
        
        for asset_path in asset_list:
            file_path = self.get_asset_path(asset_path)
            
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Add source mapping comment
                    bundled_content.append(f'/* Source: {asset_path} */')
                    bundled_content.append(content)
                    bundled_content.append('')
                    
                except Exception as e:
                    current_app.logger.error(f"Error reading asset {asset_path}: {str(e)}")
            else:
                current_app.logger.warning(f"Asset file not found: {asset_path}")
        
        # Join all content
        final_content = '\n'.join(bundled_content)
        
        # Minify based on type
        if asset_type == 'css':
            final_content = self.minify_css(final_content)
        elif asset_type == 'js':
            final_content = self.minify_js(final_content)
        
        return final_content
    
    def generate_bundle_hash(self, content):
        """
        Generate hash for bundle content.
        
        Args:
            content: Bundle content
            
        Returns:
            Hash string
        """
        return hashlib.md5(content.encode('utf-8')).hexdigest()[:8]
    
    def save_bundle(self, asset_type, bundle_name, content):
        """
        Save bundled content to file.
        
        Args:
            asset_type: 'css' or 'js'
            bundle_name: Name of the bundle
            content: Bundle content
            
        Returns:
            Path to saved bundle file
        """
        # Generate hash for cache busting
        content_hash = self.generate_bundle_hash(content)
        
        # Create bundle filename
        bundle_filename = f"{bundle_name}.{content_hash}.min.{asset_type}"
        
        # Create bundles directory
        bundles_dir = self.get_static_path() / 'bundles'
        bundles_dir.mkdir(exist_ok=True)
        
        # Save bundle file
        bundle_path = bundles_dir / bundle_filename
        
        try:
            with open(bundle_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Update manifest
            self.manifest[f"{asset_type}_{bundle_name}"] = {
                'filename': bundle_filename,
                'hash': content_hash,
                'created': time.time()
            }
            
            self.save_manifest()
            
            return f"bundles/{bundle_filename}"
            
        except Exception as e:
            current_app.logger.error(f"Error saving bundle: {str(e)}")
            return None
    
    def load_manifest(self):
        """Load asset manifest from file."""
        manifest_path = self.get_static_path() / 'bundles' / 'manifest.json'
        
        if manifest_path.exists():
            try:
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    self.manifest = json.load(f)
            except Exception as e:
                current_app.logger.error(f"Error loading manifest: {str(e)}")
                self.manifest = {}
    
    def save_manifest(self):
        """Save asset manifest to file."""
        bundles_dir = self.get_static_path() / 'bundles'
        bundles_dir.mkdir(exist_ok=True)
        
        manifest_path = bundles_dir / 'manifest.json'
        
        try:
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(self.manifest, f, indent=2)
        except Exception as e:
            current_app.logger.error(f"Error saving manifest: {str(e)}")
    
    def cleanup_old_bundles(self):
        """Clean up old bundle files."""
        bundles_dir = self.get_static_path() / 'bundles'
        
        if not bundles_dir.exists():
            return
        
        # Get current bundle files from manifest
        current_files = set()
        for bundle_info in self.manifest.values():
            current_files.add(bundle_info['filename'])
        
        # Remove old bundle files
        for file_path in bundles_dir.glob('*.min.*'):
            if file_path.name not in current_files and file_path.name != 'manifest.json':
                try:
                    file_path.unlink()
                    current_app.logger.info(f"Removed old bundle: {file_path.name}")
                except Exception as e:
                    current_app.logger.error(f"Error removing old bundle: {str(e)}")
    
    def bundle_url(self, asset_type, bundle_name):
        """
        Get URL for a bundle.
        
        Args:
            asset_type: 'css' or 'js'
            bundle_name: Name of the bundle
            
        Returns:
            URL to bundle file
        """
        manifest_key = f"{asset_type}_{bundle_name}"
        
        # Check if bundle exists in manifest
        if manifest_key not in self.manifest:
            # Create bundle
            bundles_config = self.app.config.get('ASSET_BUNDLES', {})
            asset_list = bundles_config.get(asset_type, {}).get(bundle_name, [])
            
            if asset_list:
                content = self.bundle_assets(asset_type, bundle_name, asset_list)
                bundle_path = self.save_bundle(asset_type, bundle_name, content)
                
                if bundle_path:
                    return url_for('static', filename=bundle_path)
        
        # Get bundle from manifest
        bundle_info = self.manifest.get(manifest_key)
        if bundle_info:
            return url_for('static', filename=f"bundles/{bundle_info['filename']}")
        
        # Fallback to individual assets
        return None
    
    def asset_url(self, asset_path):
        """
        Get URL for an individual asset with cache busting.
        
        Args:
            asset_path: Path to asset file
            
        Returns:
            URL to asset file
        """
        file_path = self.get_asset_path(asset_path)
        
        if file_path.exists():
            # Generate hash for cache busting
            try:
                with open(file_path, 'rb') as f:
                    content = f.read()
                file_hash = hashlib.md5(content).hexdigest()[:8]
                
                return url_for('static', filename=asset_path, v=file_hash)
            except Exception as e:
                current_app.logger.error(f"Error reading asset for hash: {str(e)}")
        
        return url_for('static', filename=asset_path)
    
    def build_all_bundles(self):
        """Build all configured bundles."""
        bundles_config = self.app.config.get('ASSET_BUNDLES', {})
        
        for asset_type, bundles in bundles_config.items():
            for bundle_name, asset_list in bundles.items():
                content = self.bundle_assets(asset_type, bundle_name, asset_list)
                self.save_bundle(asset_type, bundle_name, content)
                current_app.logger.info(f"Built bundle: {asset_type}_{bundle_name}")
        
        # Clean up old bundles
        self.cleanup_old_bundles()


# Global asset manager instance
asset_manager = AssetManager()


def init_assets(app):
    """Initialize asset management for Flask app."""
    asset_manager.init_app(app)
    
    # CLI command to build bundles
    @app.cli.command()
    def build_assets():
        """Build all asset bundles."""
        asset_manager.build_all_bundles()
        print("Asset bundles built successfully!")
    
    return asset_manager