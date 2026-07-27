package com.kltn.travelassistant.data.packages

import com.kltn.travelassistant.feature.downloads.domain.PackageCity
import com.kltn.travelassistant.feature.downloads.domain.PackageSyncPhase
import java.io.File
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.CancellationException

@Singleton
class PackageSyncEngine @Inject constructor(
    private val locationProvider: PackageManifestLocationProvider,
    private val downloader: PackageDownloader,
    private val manifestParser: PackageManifestParser,
    private val manifestValidator: PackageManifestValidator,
    private val stagingStore: PackageStagingStore,
    private val checksumVerifier: PackageChecksumVerifier,
    private val artifactParser: PackageArtifactParser,
    private val artifactValidator: PackageArtifactValidator,
    private val activator: PackageActivator,
) {
    suspend fun synchronize(
        city: PackageCity,
        onProgress: suspend (PackageSyncPhase) -> Unit,
    ) {
        val location = locationProvider.locationFor(city)
            ?: throw PackageSyncException(PackageSyncError.UNSUPPORTED_PACKAGE)
        var manifest: ValidatedPackageManifest? = null
        try {
            onProgress(PackageSyncPhase.DOWNLOADING_MANIFEST)
            val rawManifest = downloader.downloadManifest(location)
            val parsedManifest = manifestParser.parse(rawManifest)
            manifest = manifestValidator.validate(parsedManifest, rawManifest, location)
            stagingStore.cleanObsolete(manifest)

            val verifiedFile = obtainVerifiedFile(manifest, onProgress)
            onProgress(PackageSyncPhase.VALIDATING)
            val artifact = artifactParser.parse(verifiedFile)
            val validatedPackage = artifactValidator.validate(artifact, manifest)

            onProgress(PackageSyncPhase.ACTIVATING)
            val activationResult = try {
                activator.activate(validatedPackage)
            } catch (exception: CancellationException) {
                throw exception
            } catch (exception: Exception) {
                throw PackageSyncException(PackageSyncError.ACTIVATION_FAILED, exception)
            }
            if (activationResult == PackageActivationResult.REJECTED_OLDER_OR_CONFLICTING) {
                throw PackageSyncException(PackageSyncError.UNSUPPORTED_PACKAGE)
            }
            verifiedFile.delete()
            stagingStore.cleanCity(city.code)
        } catch (exception: CancellationException) {
            throw exception
        } catch (exception: PackageSyncException) {
            if (!exception.error.retryable) {
                stagingStore.cleanCity(city.code)
            } else if (manifest != null) {
                stagingStore.cleanObsolete(manifest)
            }
            throw exception
        }
    }

    private suspend fun obtainVerifiedFile(
        manifest: ValidatedPackageManifest,
        onProgress: suspend (PackageSyncPhase) -> Unit,
    ): File {
        val existingVerified = stagingStore.verifiedFile(manifest)
        if (existingVerified.exists()) {
            onProgress(PackageSyncPhase.VERIFYING)
            if (checksumVerifier.verify(existingVerified, manifest)) return existingVerified
            existingVerified.delete()
        }

        onProgress(PackageSyncPhase.DOWNLOADING_DATA)
        val partFile = downloader.downloadData(manifest, stagingStore.partFile(manifest))
        onProgress(PackageSyncPhase.VERIFYING)
        if (!checksumVerifier.verify(partFile, manifest)) {
            partFile.delete()
            throw PackageSyncException(PackageSyncError.CHECKSUM_MISMATCH)
        }
        return stagingStore.promoteToVerified(manifest, partFile)
    }
}
