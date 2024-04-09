import inspect
import logging
import os
import sys
from functools import wraps
import re
from pxr import Ar

# Utils
SYSTEM_IS_LINUX = sys.platform.lower() == "linux"
SYSTEM_IS_WINDOWS = any([w in sys.platform.lower() for w in ["windows", "win32", "win64", "cygwin"]])

SEARCH_PATHS = os.getenv("AR_SEARCH_PATHS","").split('?')
AR_CACHE_ASSETPATHS = int(os.getenv("AR_CACHE_ASSETPATHS","1"))

if SYSTEM_IS_LINUX:
	SEARCH_PATHS = SEARCH_PATHS[0].split(":")
else:
	SEARCH_PATHS = SEARCH_PATHS[1].split(";")

def resolveSearchPath(assetPath):
	resolved_asset_path = assetPath

	for anchor in SEARCH_PATHS:
		resolved_asset_path =  os.path.normpath(os.path.join(anchor, assetPath))
		if os.path.isfile(resolved_asset_path):
			return resolved_asset_path

	return assetPath

def resolveLatest(pubfolder):

	# early out if the pub folder does not exist
	if not os.path.isdir(pubfolder):
		return 'latest'

	versions = os.listdir(pubfolder)

	# Filter elements that start with 'v'
	version_list = [e for e in versions if re.match(r'^v\d+', e)]

	if not version_list:
		return 'latest'  # No elements start with 'v'

	# Find the element with the highest number
	max_elem = max(version_list, key=lambda x: int(x[1:]))

	return max_elem

def findLatestRecursive(filepath):

	# early out if the pub folder does not exist
	if not os.path.isfile(filepath):
		return filepath

	pubfolder = getVersionFolder(filepath)
	
	versions = os.listdir(pubfolder)

	# Filter elements that start with 'v'
	version_list = [e for e in versions if re.match(r'^v\d+', e)]
	version_list.sort()  # Orders the list
	version_list.reverse()  # Reverses the list
	
	if not version_list:
		return filepath

	# Find the element with the highest number
	#max_elem = max(version_list, key=lambda x: int(x[1:]))
	for version in version_list:
		newpath = filepath.replace('latest', version)
		if os.path.isfile(newpath):
			return newpath 

	return filepath

def resolveLatestPath(filepath):
	
	search_terms = ["cache/cfxsim", "cache/groom"]  # Specialy roles for cfxsim and groom
	
	found = any(term in filepath for term in search_terms)
	
	if found:
		return findLatestRecursive(filepath)
		
	else:
		versionFolder = getVersionFolder(filepath)        
		version = resolveLatest(versionFolder)
		
		return filepath.replace('latest', version)

def getAncestorFolder(path, ancestorLevel):
	#TODO this can be made more efficient, we dont realy need a loop here

	for i in range(0,ancestorLevel): 
		path = os.path.dirname(path)

	return path

def getVersionFolder(path):

	folderName = os.path.dirname(path)
	versionFolder = folderName.lower().split('latest')[0]

	return versionFolder

# Init logger
logging.basicConfig(format="%(asctime)s %(message)s", datefmt="%Y/%m/%d %I:%M:%S%p")
LOG = logging.getLogger("Python | {file_name}".format(file_name=__name__))
LOG.setLevel(level=logging.INFO)


def log_function_args(func):
	"""Decorator to print function call details."""

	@wraps(func)
	def wrapper(*args, **kwargs):
		func_args = inspect.signature(func).bind(*args, **kwargs).arguments
		func_args_str = ", ".join(map("{0[0]} = {0[1]!r}".format, func_args.items()))
		# To enable logging on all methods, re-enable this.
		# LOG.info(f"{func.__module__}.{func.__qualname__} ({func_args_str})")
		return func(*args, **kwargs)

	return wrapper


class UnitTestHelper:
	create_relative_path_identifier_call_counter = 0
	context_initialize_call_counter = 0
	resolve_and_cache_call_counter = 0
	current_directory_path = ""

	@classmethod
	def reset(cls, current_directory_path=""):
		cls.create_relative_path_identifier_call_counter = 0
		cls.context_initialize_call_counter = 0
		cls.resolve_and_cache_call_counter = 0
		cls.current_directory_path = current_directory_path


class Resolver:

	@staticmethod
	@log_function_args
	def CreateRelativePathIdentifier(resolver, anchoredAssetPath, assetPath, anchorAssetPath):
		"""Returns an identifier for the asset specified by assetPath and anchor asset path.
		It is very important that the anchoredAssetPath is used as the cache key, as this
		is what is used in C++ to do the cache lookup.

		We have two options how to return relative identifiers:
		- Make it absolute: Simply return the anchoredAssetPath. This means the relative identifier
							will not be passed through to ResolverContext.ResolveAndCache.
		- Make it non file based: Make sure the remapped identifier does not start with "/", "./" or"../"
								  by putting some sort of prefix in front of it. The path will then be
								  passed through to ResolverContext.ResolveAndCache, where you need to re-construct
								  it to an absolute path of your liking. Make sure you don't use a "<somePrefix>:" syntax,
								  to avoid mixups with URI based resolvers.

		Args:
			resolver (CachedResolver): The resolver
			anchoredAssetPath (str): The anchored asset path, this has to be used as the cached key.
			assetPath (str): An unresolved asset path.
			anchorAssetPath (Ar.ResolvedPath): A resolved anchor path.

		Returns:
			str: The identifier.
		"""

		#LOG.debug("::: Resolver.CreateRelativePathIdentifier | {} | {} | {}".format(anchoredAssetPath, assetPath, anchorAssetPath))
		"""The code below is only needed to verify that UnitTests work."""
		UnitTestHelper.create_relative_path_identifier_call_counter += 1

		ancestorLevel = assetPath.count('../')

		assetPath = assetPath.replace('../','')
		remappedRelativePathIdentifier = f"relativePath|{assetPath}?{anchorAssetPath}!{ancestorLevel}"

		resolver.AddCachedRelativePathIdentifierPair(anchoredAssetPath, remappedRelativePathIdentifier)

		return remappedRelativePathIdentifier


class ResolverContext:

	@staticmethod
	@log_function_args
	def Initialize(context):
		"""Initialize the context. This get's called on default and post mapping file path
		context creation.

		Here you can inject data by batch calling context.AddCachingPair(assetPath, resolvePath),
		this will then populate the internal C++ resolve cache and all resolves calls
		to those assetPaths will not invoke Python and instead use the cache.

		Args:
			context (CachedResolverContext): The active context.
		"""
		LOG.debug("::: ResolverContext.Initialize")

		return

	@staticmethod
	@log_function_args
	def ResolveAndCache(context, assetPath):
		"""Return the resolved path for the given assetPath or an empty
		ArResolvedPath if no asset exists at that path.
		Args:
			context (CachedResolverContext): The active context.
			assetPath (str): An unresolved asset path.
		Returns:
			str: The resolved path string. If it points to a non-existent file,
				 it will be resolved to  qan empty ArResolvedPath internally, but will
				 still count as a cache hit and be stored inside the cachedPairs dict.
		"""
		LOG.debug(
			"::: ResolverContext.ResolveAndCache | {} | {}".format(assetPath, context.GetCachingPairs())
		)

		assetPath = assetPath.replace('\\','/')
	
		if assetPath == 'reload':
			context.ClearCachingPairs()
			print ('Clear Asset Resolver')
			return 'S:/pipeline/qscripts/qsd/qsd-dev/qsd/asset_resolver/reload.usd'


		if assetPath.startswith("relativePath|"):

			relative_path, anchor_path = assetPath.removeprefix("relativePath|").split("?")
			anchor_path, ancestorLevel = anchor_path.split('!')

			anchor_path = anchor_path[:-1] if anchor_path[-1] == "/" else anchor_path[:anchor_path.rfind("/")]
			anchor_path = getAncestorFolder(anchor_path, int(ancestorLevel))

			if anchor_path[0] == '/' and SYSTEM_IS_WINDOWS:
				anchor_path = f'/{anchor_path}'

			resolved_asset_path = os.path.normpath(os.path.join(anchor_path, relative_path))

			if 'latest' in resolved_asset_path:
				resolved_asset_path = resolveLatestPath(resolved_asset_path)

			if os.path.isfile(resolved_asset_path):
				context.AddCachingPair(assetPath, resolved_asset_path)
		else:
			resolved_asset_path = resolveSearchPath(assetPath)
		   
			if 'latest' in resolved_asset_path:
				resolved_asset_path = resolveLatestPath(resolved_asset_path)

			if os.path.isfile(resolved_asset_path):
				context.AddCachingPair(assetPath, resolved_asset_path)
				
		if os.getenv('PRINT_RESOLVED_PATH', 'False') == 'True':
			print ('newResolvedPath: %s' % resolved_asset_path)

		return resolved_asset_path


"""
import sys
sys.path.append('S:/pipeline/plugins/houdini/Packages/assetResolver_v0.6/cachedResolver/lib/python')

import PythonExpose
from importlib import reload  # Python 3.4+
reload(PythonExpose)"""